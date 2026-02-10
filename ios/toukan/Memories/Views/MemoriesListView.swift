//
//  MemoriesListView.swift
//  Memories
//

import SwiftUI
import SwiftData

struct MemoriesListView: View {
    var uploadManager: UploadManager

    @State private var memories: [Memory] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var selectedMemory: Memory?

    var body: some View {
        Group {
            if memories.isEmpty {
                emptyState
            } else {
                memoriesList
            }
        }
        .navigationTitle("Memories")
        .task {
            await fetchMemories()
        }
        .sheet(item: $selectedMemory) { memory in
            MemoryDetailView(memory: memory)
        }
    }

    // MARK: - List

    private var memoriesList: some View {
        List {
            ForEach(memories) { memory in
                MemoryRow(memory: memory)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        selectedMemory = memory
                    }
                    .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                        Button(role: .destructive) {
                            Task {
                                await deleteMemory(memory)
                            }
                        } label: {
                            Label("Delete", systemImage: "trash")
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
            Image(systemName: "brain.head.profile")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("No memories yet")
                .font(.title3.weight(.semibold))

            Text("Record audio to create memories with AI-powered summaries.")
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

    private func deleteMemory(_ memory: Memory) async {
        do {
            try await MemoryAPIClient.deleteMemory(id: memory.id)
            // Remove from local state on success
            memories.removeAll { $0.id == memory.id }
        } catch {
            errorMessage = "Failed to delete memory: \(error.localizedDescription)"
        }
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
