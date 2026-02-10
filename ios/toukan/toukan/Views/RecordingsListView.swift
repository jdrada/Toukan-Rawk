//
//  RecordingsListView.swift
//  toukan
//

import SwiftUI
import SwiftData

struct RecordingsListView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \Recording.recordedAt, order: .reverse) private var recordings: [Recording]
    var uploadManager: UploadManager

    var body: some View {
        Group {
            if recordings.isEmpty {
                emptyState
            } else {
                recordingsList
            }
        }
        .navigationTitle("Recordings")
    }

    // MARK: - List

    private var recordingsList: some View {
        List {
            ForEach(recordings) { recording in
                RecordingRow(recording: recording) {
                    retryUpload(for: recording)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                    Button(role: .destructive) {
                        deleteRecording(recording)
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                }
            }
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "waveform")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("No recordings yet")
                .font(.title3.weight(.semibold))

            Text("Tap the mic button to start recording.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
    }

    // MARK: - Actions

    private func retryUpload(for recording: Recording) {
        recording.uploadStatus = .pending
        recording.retryCount = 0
        try? modelContext.save()
        uploadManager.enqueueUpload(for: recording, in: modelContext)
    }

    private func deleteRecording(_ recording: Recording) {
        // Delete the audio file from disk
        let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let fileURL = documentsURL.appendingPathComponent(recording.filePath)

        try? FileManager.default.removeItem(at: fileURL)

        // Delete from SwiftData
        modelContext.delete(recording)
        try? modelContext.save()

        print("[RecordingsListView] Deleted recording: \(recording.filePath)")
    }
}

#Preview {
    NavigationStack {
        RecordingsListView(uploadManager: UploadManager.shared)
    }
    .modelContainer(for: Recording.self, inMemory: true)
}
