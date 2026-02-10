//
//  StopRecordingIntent.swift
//  toukan
//

import AppIntents
import SwiftData

struct StopRecordingIntent: AppIntent {
    static var title: LocalizedStringResource = "Stop Recording"
    static var description: IntentDescription = "Stop recording audio with Toukan"
    static var openAppWhenRun = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let recordingManager = await RecordingManager.shared

        guard await recordingManager.isRecording else {
            return .result(dialog: "Toukan isn't recording right now.")
        }

        guard let result = await recordingManager.stopRecording() else {
            return .result(dialog: "Could not save the recording.")
        }

        // Save to SwiftData and enqueue upload
        await saveAndUpload(filePath: result.filePath, duration: result.duration)

        return .result(dialog: "Recording saved. I'll upload it in the background.")
    }

    @MainActor
    private func saveAndUpload(filePath: String, duration: TimeInterval) {
        let uploadManager = UploadManager.shared

        guard let container = try? ModelContainer(for: Recording.self) else { return }
        let context = ModelContext(container)

        let recording = Recording(filePath: filePath, duration: duration)
        context.insert(recording)
        try? context.save()

        uploadManager.enqueueUpload(for: recording, in: context)
    }
}
