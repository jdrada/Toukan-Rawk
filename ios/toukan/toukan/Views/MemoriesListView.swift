//
//  MemoriesListView.swift
//  toukan
//

import SwiftUI
import SwiftData

struct MemoriesListView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \Recording.recordedAt, order: .reverse) private var recordings: [Recording]
    var uploadManager: UploadManager

    @State private var memories: [Memory] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if recordings.isEmpty && memories.isEmpty {
                emptyState
            } else {
                memoriesList
            }
        }
        .navigationTitle("Memories")
        .task {
            await fetchMemories()
        }
    }

    // MARK: - List

    private var memoriesList: some View {
        List {
            if !recordings.isEmpty {
                Section("Local Recordings") {
                    ForEach(recordings) { recording in
                        RecordingRow(recording: recording) {
                            retryUpload(for: recording)
                        }
                    }
                }
            }

            if !memories.isEmpty {
                Section("Backend Memories") {
                    ForEach(memories) { memory in
                        MemoryRow(memory: memory)
                    }
                }
            }
        }
        .refreshable {
            await fetchMemories()
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "waveform")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("No memories yet")
                .font(.title3.weight(.semibold))

            Text("Tap the mic button or use Siri to start recording.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
    }

    // MARK: - Actions

    private func fetchMemories() async {
        isLoading = true
        errorMessage = nil

        do {
            let response = try await MemoryAPIClient.fetchMemories()
            memories = response.items
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    private func retryUpload(for recording: Recording) {
        recording.uploadStatus = .pending
        recording.retryCount = 0
        try? modelContext.save()
        uploadManager.enqueueUpload(for: recording, in: modelContext)
    }
}

// MARK: - Memory Row

private struct MemoryRow: View {
    let memory: Memory

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(memory.title ?? "Untitled")
                .font(.headline)

            HStack {
                statusBadge

                Spacer()

                Text(memory.createdAt, style: .date)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }

    private var statusBadge: some View {
        Text(memory.status.rawValue.capitalized)
            .font(.caption)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(statusColor.opacity(0.2))
            .foregroundStyle(statusColor)
            .clipShape(Capsule())
    }

    private var statusColor: Color {
        switch memory.status {
        case .uploading: return .cyan
        case .processing: return .orange
        case .ready: return .green
        case .failed: return .red
        }
    }
}

#Preview {
    NavigationStack {
        MemoriesListView(uploadManager: UploadManager.shared)
    }
    .modelContainer(for: Recording.self, inMemory: true)
}
