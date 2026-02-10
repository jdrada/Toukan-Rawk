//
//  RecordingManager.swift
//  toukan
//

import AVFoundation
import Foundation
import MediaPlayer
import Observation
import UIKit

@Observable
final class RecordingManager: NSObject {
    static let shared = RecordingManager()

    // MARK: - State

    var isRecording = false
    var isPaused = false
    var elapsedTime: TimeInterval = 0
    var audioLevel: Float = 0

    // MARK: - Private

    private var audioRecorder: AVAudioRecorder?
    private var timer: Timer?
    private var recordingStartTime: Date?
    private var accumulatedTime: TimeInterval = 0
    private var currentFilePath: String?
    private var backgroundTaskID: UIBackgroundTaskIdentifier = .invalid

    private override init() {
        super.init()
        setupNotifications()
    }

    // MARK: - Public API

    func startRecording() {
        guard !isRecording else { return }

        do {
            try configureAudioSession()
            let (url, relativePath) = generateFileURL()
            let recorder = try AVAudioRecorder(url: url, settings: recordingSettings)
            recorder.delegate = self
            recorder.isMeteringEnabled = true
            recorder.record()

            audioRecorder = recorder
            currentFilePath = relativePath
            isRecording = true
            isPaused = false
            accumulatedTime = 0
            recordingStartTime = Date()
            startTimer()
            updateNowPlayingInfo()
        } catch {
            print("Failed to start recording: \(error)")
        }
    }

    func stopRecording() -> (filePath: String, duration: TimeInterval)? {
        guard isRecording, let recorder = audioRecorder else { return nil }

        recorder.stop()
        stopTimer()
        endBackgroundTask()
        deactivateAudioSession()
        clearNowPlayingInfo()

        let duration = elapsedTime
        let filePath = currentFilePath ?? ""

        isRecording = false
        isPaused = false
        elapsedTime = 0
        audioLevel = 0
        audioRecorder = nil
        currentFilePath = nil
        accumulatedTime = 0
        recordingStartTime = nil

        print("[RecordingManager] Recording stopped - duration: \(duration)s, file: \(filePath)")

        guard !filePath.isEmpty else { return nil }
        return (filePath: filePath, duration: duration)
    }

    // MARK: - Audio Session

    private func configureAudioSession() throws {
        let session = AVAudioSession.sharedInstance()
        // .record category for background recording
        // .measurement mode prevents system from modifying audio
        // .mixWithOthers allows other apps to play audio while recording
        // .allowBluetooth enables bluetooth headset support
        try session.setCategory(.record, mode: .measurement, options: [.mixWithOthers, .allowBluetooth])
        try session.setActive(true, options: [])
        print("[RecordingManager] Audio session configured and activated")
    }

    private func deactivateAudioSession() {
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    // MARK: - Recording Settings

    private var recordingSettings: [String: Any] {
        [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
            AVEncoderBitRateKey: 64000,
        ]
    }

    // MARK: - File Management

    private func generateFileURL() -> (url: URL, relativePath: String) {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate, .withFullTime]
        let timestamp = formatter.string(from: Date())
            .replacingOccurrences(of: ":", with: "-")
        let filename = "toukan_\(timestamp).m4a"

        let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let fileURL = documentsURL.appendingPathComponent(filename)

        return (url: fileURL, relativePath: filename)
    }

    // MARK: - Timer

    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.updateMetrics()
        }
    }

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }

    private func updateMetrics() {
        guard isRecording, !isPaused else { return }

        if let startTime = recordingStartTime {
            elapsedTime = accumulatedTime + Date().timeIntervalSince(startTime)
        }

        audioRecorder?.updateMeters()
        let power = audioRecorder?.averagePower(forChannel: 0) ?? -160
        // Normalize from dB range (-160...0) to 0...1
        let minDb: Float = -60
        let normalizedLevel = max(0, (power - minDb) / (-minDb))
        audioLevel = normalizedLevel

        // Update lock screen with current time
        updateNowPlayingInfo()
    }

    // MARK: - Lock Screen / Now Playing

    private func updateNowPlayingInfo() {
        var nowPlayingInfo = [String: Any]()
        nowPlayingInfo[MPMediaItemPropertyTitle] = "Recording in Progress"
        nowPlayingInfo[MPMediaItemPropertyArtist] = "Toukan"
        nowPlayingInfo[MPNowPlayingInfoPropertyElapsedPlaybackTime] = elapsedTime
        nowPlayingInfo[MPNowPlayingInfoPropertyPlaybackRate] = 1.0
        nowPlayingInfo[MPMediaItemPropertyPlaybackDuration] = 0 // Unknown duration for live recording

        MPNowPlayingInfoCenter.default().nowPlayingInfo = nowPlayingInfo
    }

    private func clearNowPlayingInfo() {
        MPNowPlayingInfoCenter.default().nowPlayingInfo = nil
    }

    // MARK: - Interruption Handling

    private func setupNotifications() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleInterruption),
            name: AVAudioSession.interruptionNotification,
            object: nil
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleRouteChange),
            name: AVAudioSession.routeChangeNotification,
            object: nil
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAppDidEnterBackground),
            name: UIApplication.didEnterBackgroundNotification,
            object: nil
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAppWillEnterForeground),
            name: UIApplication.willEnterForegroundNotification,
            object: nil
        )
    }

    @objc private func handleInterruption(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let typeValue = userInfo[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: typeValue) else { return }

        switch type {
        case .began:
            if isRecording && !isPaused {
                audioRecorder?.pause()
                accumulatedTime = elapsedTime
                recordingStartTime = nil
                isPaused = true
                stopTimer()
            }
        case .ended:
            if isRecording && isPaused {
                let options = userInfo[AVAudioSessionInterruptionOptionKey] as? UInt ?? 0
                let shouldResume = AVAudioSession.InterruptionOptions(rawValue: options).contains(.shouldResume)
                if shouldResume {
                    try? AVAudioSession.sharedInstance().setActive(true)
                    audioRecorder?.record()
                    recordingStartTime = Date()
                    isPaused = false
                    startTimer()
                }
            }
        @unknown default:
            break
        }
    }

    @objc private func handleRouteChange(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let reasonValue = userInfo[AVAudioSessionRouteChangeReasonKey] as? UInt,
              let reason = AVAudioSession.RouteChangeReason(rawValue: reasonValue) else { return }

        if reason == .oldDeviceUnavailable && isRecording {
            // Input device disconnected — recording continues with default mic
            try? configureAudioSession()
        }
    }

    @objc private func handleAppDidEnterBackground(_ notification: Notification) {
        guard isRecording else { return }

        print("[RecordingManager] App entered background - maintaining recording")

        // Start a background task to ensure recording continues
        backgroundTaskID = UIApplication.shared.beginBackgroundTask(withName: "AudioRecording") { [weak self] in
            self?.endBackgroundTask()
        }

        // Ensure audio session stays active
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setActive(true, options: [])
            print("[RecordingManager] Audio session kept active in background")
        } catch {
            print("[RecordingManager] Failed to keep audio session active: \(error)")
        }

        // Verify recorder is still recording
        if let recorder = audioRecorder, !recorder.isRecording {
            print("[RecordingManager] WARNING: Recorder stopped! Attempting to restart...")
            recorder.record()
        }
    }

    @objc private func handleAppWillEnterForeground(_ notification: Notification) {
        guard isRecording else { return }

        print("[RecordingManager] App entering foreground")

        // End background task
        endBackgroundTask()

        // Verify audio session
        do {
            let session = AVAudioSession.sharedInstance()
            if !session.isOtherAudioPlaying {
                try session.setActive(true, options: [])
            }
            print("[RecordingManager] Audio session verified in foreground")
        } catch {
            print("[RecordingManager] Failed to verify audio session: \(error)")
        }

        // Verify recorder is still recording
        if let recorder = audioRecorder {
            let wasRecording = recorder.isRecording
            print("[RecordingManager] Recorder status: \(wasRecording ? "recording" : "stopped")")
            if !wasRecording {
                print("[RecordingManager] WARNING: Recorder was stopped during background!")
            }
        }
    }

    private func endBackgroundTask() {
        if backgroundTaskID != .invalid {
            UIApplication.shared.endBackgroundTask(backgroundTaskID)
            backgroundTaskID = .invalid
            print("[RecordingManager] Background task ended")
        }
    }
}

// MARK: - AVAudioRecorderDelegate

extension RecordingManager: AVAudioRecorderDelegate {
    nonisolated func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        if !flag {
            print("Recording did not finish successfully")
        }
    }

    nonisolated func audioRecorderEncodeErrorDidOccur(_ recorder: AVAudioRecorder, error: (any Error)?) {
        print("Recording encode error: \(String(describing: error))")
    }
}
