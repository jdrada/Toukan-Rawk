//
//  RecordingView.swift
//  Memories
//

import SwiftUI
import SwiftData

struct RecordingView: View {
    @Environment(\.modelContext) private var modelContext
    var recordingManager: RecordingManager
    var uploadManager: UploadManager

    @State private var showSavedConfirmation = false

    var body: some View {
        ZStack {
            backgroundGradient
                .ignoresSafeArea()

            VStack(spacing: 40) {
                Spacer()

                if recordingManager.isRecording {
                    recordingState
                } else {
                    idleState
                }

                Spacer()
            }
            .padding()

            if showSavedConfirmation {
                savedOverlay
            }
        }
    }

    // MARK: - Idle State

    private var idleState: some View {
        VStack(spacing: 32) {
            Text("Memories")
                .font(.system(size: 36, weight: .bold, design: .rounded))
                .foregroundStyle(.primary)

            Button(action: startRecording) {
                ZStack {
                    Circle()
                        .fill(.red.opacity(0.15))
                        .frame(width: 160, height: 160)

                    Circle()
                        .fill(.red)
                        .frame(width: 100, height: 100)
                        .shadow(color: .red.opacity(0.3), radius: 10, y: 4)

                    Image(systemName: "mic.fill")
                        .font(.system(size: 36))
                        .foregroundStyle(.white)
                }
            }
            .accessibilityLabel("Start Recording")

            Text("Or say \"Hey Siri, start recording with Memories\"")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
    }

    // MARK: - Recording State

    private var recordingState: some View {
        VStack(spacing: 32) {
            Text(formattedTime)
                .font(.system(size: 60, weight: .light, design: .monospaced))
                .foregroundStyle(.primary)
                .contentTransition(.numericText())

            // Audio level indicator
            PulsingCircle(level: recordingManager.audioLevel)
                .frame(width: 120, height: 120)

            if recordingManager.isPaused {
                Text("Paused")
                    .font(.headline)
                    .foregroundStyle(.orange)
            }

            Button(action: stopRecording) {
                HStack(spacing: 10) {
                    Image(systemName: "stop.fill")
                        .font(.title3)
                    Text("Stop Recording")
                        .font(.headline)
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 32)
                .padding(.vertical, 16)
                .background(.red, in: Capsule())
                .shadow(color: .red.opacity(0.3), radius: 8, y: 4)
            }
            .accessibilityLabel("Stop Recording")
        }
    }

    // MARK: - Saved Confirmation

    private var savedOverlay: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(.green)
            Text("Recording saved")
                .font(.title3.weight(.semibold))
        }
        .padding(40)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20))
        .transition(.scale.combined(with: .opacity))
    }

    // MARK: - Background

    private var backgroundGradient: some View {
        Group {
            if recordingManager.isRecording {
                Color.red.opacity(0.05)
                    .animation(.easeInOut(duration: 0.5), value: recordingManager.isRecording)
            } else {
                Color(.systemBackground)
            }
        }
    }

    // MARK: - Actions

    private func startRecording() {
        recordingManager.startRecording()
    }

    private func stopRecording() {
        guard let result = recordingManager.stopRecording() else { return }

        let recording = Recording(
            filePath: result.filePath,
            duration: result.duration
        )
        modelContext.insert(recording)
        try? modelContext.save()

        uploadManager.enqueueUpload(for: recording, in: modelContext)

        withAnimation(.spring(duration: 0.4)) {
            showSavedConfirmation = true
        }
        Task {
            try? await Task.sleep(for: .seconds(1.5))
            withAnimation(.easeOut(duration: 0.3)) {
                showSavedConfirmation = false
            }
        }
    }

    // MARK: - Formatting

    private var formattedTime: String {
        let totalSeconds = Int(recordingManager.elapsedTime)
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
}

// MARK: - Pulsing Circle

struct PulsingCircle: View {
    let level: Float

    var body: some View {
        ZStack {
            Circle()
                .fill(.red.opacity(0.1))
                .scaleEffect(1.0 + CGFloat(level) * 0.5)

            Circle()
                .fill(.red.opacity(0.2))
                .scaleEffect(0.8 + CGFloat(level) * 0.3)

            Circle()
                .fill(.red.opacity(0.4))
                .frame(width: 40, height: 40)
                .scaleEffect(1.0 + CGFloat(level) * 0.2)
        }
        .animation(.easeOut(duration: 0.15), value: level)
    }
}

#Preview {
    RecordingView(
        recordingManager: RecordingManager.shared,
        uploadManager: UploadManager.shared
    )
    .modelContainer(for: Recording.self, inMemory: true)
}
