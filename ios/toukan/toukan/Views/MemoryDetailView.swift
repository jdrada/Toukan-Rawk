//
//  MemoryDetailView.swift
//  toukan
//

import SwiftUI

struct MemoryDetailView: View {
    let memory: Memory
    @Environment(\.dismiss) private var dismiss
    @State private var isTranscriptExpanded = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // Title and Status
                    VStack(alignment: .leading, spacing: 8) {
                        Text(memory.title ?? "Untitled")
                            .font(.title.bold())

                        HStack {
                            statusBadge

                            Spacer()

                            Text(memory.createdAt, style: .date)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    // 1. Summary (primero)
                    if let summary = memory.summary {
                        sectionView(title: "Summary", icon: "doc.text") {
                            Text(summary)
                                .font(.body)
                        }
                    }

                    // 2. Key Points (segundo)
                    if let keyPoints = memory.keyPoints, !keyPoints.isEmpty {
                        sectionView(title: "Key Points", icon: "star") {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(keyPoints, id: \.self) { point in
                                    HStack(alignment: .top, spacing: 8) {
                                        Text("•")
                                        Text(point)
                                    }
                                }
                            }
                        }
                    }

                    // Action Items
                    if let actionItems = memory.actionItems, !actionItems.isEmpty {
                        sectionView(title: "Action Items", icon: "checkmark.circle") {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(actionItems, id: \.self) { item in
                                    HStack(alignment: .top, spacing: 8) {
                                        Image(systemName: "circle")
                                            .font(.caption)
                                        Text(item)
                                    }
                                }
                            }
                        }
                    }

                    // 3. Transcript (último, como acordeón)
                    if let transcript = memory.transcript {
                        DisclosureGroup(
                            isExpanded: $isTranscriptExpanded,
                            content: {
                                Text(transcript)
                                    .font(.body)
                                    .padding(.top, 8)
                                    .padding(.leading, 28)
                            },
                            label: {
                                Label("Transcript", systemImage: "text.alignleft")
                                    .font(.headline)
                                    .foregroundStyle(.primary)
                            }
                        )
                        .padding(.vertical, 8)
                    }

                    // Duration
                    if let duration = memory.duration {
                        sectionView(title: "Duration", icon: "clock") {
                            Text(formattedDuration(duration))
                                .font(.body)
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Memory Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }

    // MARK: - Helpers

    private func sectionView<Content: View>(title: String, icon: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: icon)
                .font(.headline)
                .foregroundStyle(.primary)

            content()
                .padding(.leading, 28)
        }
        .padding(.vertical, 8)
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

    private func formattedDuration(_ seconds: Double) -> String {
        let totalSeconds = Int(seconds)
        let minutes = totalSeconds / 60
        let secs = totalSeconds % 60
        if minutes > 0 {
            return "\(minutes)m \(secs)s"
        }
        return "\(secs)s"
    }
}

#Preview {
    MemoryDetailView(memory: Memory(
        id: "preview-id",
        title: "Sample Memory",
        status: .ready,
        audioUrl: "s3://bucket/audio.m4a",
        transcript: "This is a sample transcript of what was said during the recording.",
        summary: "A brief summary of the key points discussed.",
        keyPoints: ["First key point", "Second key point", "Third key point"],
        actionItems: ["Action to take", "Another action"],
        duration: 125.5,
        createdAt: Date(),
        updatedAt: Date()
    ))
}
