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

    @State private var processingState: ProcessingState?
    @State private var pollTimer: Timer?

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

            // Top notification banner
            VStack {
                if let state = processingState {
                    ProcessingBanner(state: state) {
                        withAnimation(.easeOut(duration: 0.3)) {
                            processingState = nil
                            stopPolling()
                        }
                    }
                    .transition(.move(edge: .top).combined(with: .opacity))
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
                }
                Spacer()
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

            // Stop button
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

            // Cancel button
            Button(action: cancelRecording) {
                Text("Cancel")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.secondary)
            }
            .accessibilityLabel("Cancel Recording")
        }
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

    private func cancelRecording() {
        recordingManager.cancelRecording()
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
            processingState = ProcessingState(
                recordingId: recording.id,
                step: .saved
            )
        }

        // Start advancing through steps
        startProgressTracking(recordingId: recording.id)
    }

    // MARK: - Progress Tracking

    private func startProgressTracking(recordingId: UUID) {
        // After a brief "Saved!" moment, start polling for status
        Task {
            try? await Task.sleep(for: .seconds(1.0))
            await MainActor.run {
                withAnimation {
                    processingState?.step = .uploading
                }
                startPolling(recordingId: recordingId)
            }
        }
    }

    private func startPolling(recordingId: UUID) {
        stopPolling()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
            Task { @MainActor in
                await pollStatus(recordingId: recordingId)
            }
        }
    }

    private func stopPolling() {
        pollTimer?.invalidate()
        pollTimer = nil
    }

    @MainActor
    private func pollStatus(recordingId: UUID) async {
        // Check local upload status first
        let context = modelContext
        let predicate = #Predicate<Recording> { $0.id == recordingId }
        let descriptor = FetchDescriptor<Recording>(predicate: predicate)

        guard let recording = try? context.fetch(descriptor).first else { return }

        switch recording.uploadStatus {
        case .pending, .uploading:
            withAnimation {
                processingState?.step = .uploading
            }
        case .failed:
            withAnimation {
                processingState?.step = .failed
            }
            stopPolling()
            // Auto-dismiss after 3s
            Task {
                try? await Task.sleep(for: .seconds(3))
                withAnimation(.easeOut(duration: 0.3)) {
                    processingState = nil
                }
            }
        case .uploaded:
            // Upload done, now poll the API for memory processing status
            await pollMemoryStatus()
        }
    }

    @MainActor
    private func pollMemoryStatus() async {
        do {
            let response = try await MemoryAPIClient.fetchMemories(page: 1, pageSize: 1)
            guard let latest = response.items.first else { return }

            switch latest.status {
            case .uploading, .processing:
                withAnimation {
                    processingState?.step = .processing
                }
            case .ready:
                withAnimation {
                    processingState?.step = .ready
                }
                stopPolling()
                // Auto-dismiss after 2s
                Task {
                    try? await Task.sleep(for: .seconds(2))
                    withAnimation(.easeOut(duration: 0.3)) {
                        processingState = nil
                    }
                }
            case .failed:
                withAnimation {
                    processingState?.step = .failed
                }
                stopPolling()
                Task {
                    try? await Task.sleep(for: .seconds(3))
                    withAnimation(.easeOut(duration: 0.3)) {
                        processingState = nil
                    }
                }
            }
        } catch {
            // Keep polling on network errors
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

// MARK: - Processing State

struct ProcessingState {
    let recordingId: UUID
    var step: Step

    enum Step {
        case saved
        case uploading
        case processing
        case ready
        case failed
    }
}

// MARK: - Processing Banner

struct ProcessingBanner: View {
    let state: ProcessingState
    let onDismiss: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Icon
            ZStack {
                Circle()
                    .fill(iconColor)
                    .frame(width: 36, height: 36)

                if state.step == .uploading || state.step == .processing {
                    ProgressView()
                        .tint(.white)
                        .scaleEffect(0.8)
                } else {
                    Image(systemName: iconName)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white)
                }
            }

            // Text
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            // Dismiss button for terminal states
            if state.step == .ready || state.step == .failed {
                Button(action: onDismiss) {
                    Image(systemName: "xmark")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .padding(6)
                        .background(.secondary.opacity(0.1), in: Circle())
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.08), radius: 12, y: 4)
    }

    private var iconName: String {
        switch state.step {
        case .saved: return "checkmark"
        case .uploading: return "arrow.up"
        case .processing: return "brain"
        case .ready: return "checkmark"
        case .failed: return "exclamationmark"
        }
    }

    private var iconColor: Color {
        switch state.step {
        case .saved: return .green
        case .uploading: return .blue
        case .processing: return .orange
        case .ready: return .green
        case .failed: return .red
        }
    }

    private var title: String {
        switch state.step {
        case .saved: return "Recording Saved"
        case .uploading: return "Uploading..."
        case .processing: return "Processing with AI..."
        case .ready: return "Memory Ready!"
        case .failed: return "Processing Failed"
        }
    }

    private var subtitle: String {
        switch state.step {
        case .saved: return "Preparing upload"
        case .uploading: return "Sending to server"
        case .processing: return "Transcribing & summarizing"
        case .ready: return "View it in Memories tab"
        case .failed: return "Tap retry in Memories tab"
        }
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
