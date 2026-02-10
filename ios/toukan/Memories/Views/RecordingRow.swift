//
//  RecordingRow.swift
//  toukan
//

import SwiftUI

struct RecordingRow: View {
    let recording: Recording
    var onRetry: (() -> Void)?

    var body: some View {
        HStack(spacing: 12) {
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
