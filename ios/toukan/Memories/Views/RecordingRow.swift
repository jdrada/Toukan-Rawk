//
//  RecordingRow.swift
//  toukan
//

import AVFoundation
import SwiftUI

struct RecordingRow: View {
    let recording: Recording
    var onRetry: (() -> Void)?

    @State private var isPlaying = false
    @State private var player: AVAudioPlayer?

    var body: some View {
        HStack(spacing: 12) {
            // Play button
            Button(action: togglePlayback) {
                Image(systemName: isPlaying ? "stop.circle.fill" : "play.circle.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(isPlaying ? .red : .blue)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 4) {
                Text(recording.recordedAt, format: .dateTime.month(.abbreviated).day().hour().minute())
                    .font(.headline)

                Text(formattedDuration)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            statusBadge
        }
        .padding(.vertical, 4)
        .onDisappear {
            stopPlayback()
        }
    }

    // MARK: - Playback

    private func togglePlayback() {
        if isPlaying {
            stopPlayback()
        } else {
            startPlayback()
        }
    }

    private func startPlayback() {
        let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let fileURL = documentsURL.appendingPathComponent(recording.filePath)

        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }

        do {
            try AVAudioSession.sharedInstance().setCategory(.playback)
            try AVAudioSession.sharedInstance().setActive(true)
            let audioPlayer = try AVAudioPlayer(contentsOf: fileURL)
            audioPlayer.play()
            player = audioPlayer
            isPlaying = true

            // Auto-stop when done
            Task {
                try? await Task.sleep(for: .seconds(audioPlayer.duration + 0.1))
                await MainActor.run {
                    if isPlaying {
                        isPlaying = false
                        player = nil
                    }
                }
            }
        } catch {
            print("[RecordingRow] Playback error: \(error)")
        }
    }

    private func stopPlayback() {
        player?.stop()
        player = nil
        isPlaying = false
    }

    // MARK: - Status Badge

    @ViewBuilder
    private var statusBadge: some View {
        switch recording.uploadStatus {
        case .pending:
            Label("Pending", systemImage: "clock")
                .font(.caption)
                .foregroundStyle(.secondary)

        case .uploading:
            HStack(spacing: 6) {
                ProgressView()
                    .controlSize(.small)
                Text("Uploading")
                    .font(.caption)
            }
            .foregroundStyle(.blue)

        case .uploaded:
            Label("Uploaded", systemImage: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(.green)

        case .failed:
            Button(action: { onRetry?() }) {
                Label("Retry", systemImage: "arrow.clockwise.circle.fill")
                    .font(.caption)
                    .foregroundStyle(.red)
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Formatting

    private var formattedDuration: String {
        let totalSeconds = Int(recording.duration)
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        if minutes > 0 {
            return "\(minutes)m \(seconds)s"
        }
        return "\(seconds)s"
    }
}
