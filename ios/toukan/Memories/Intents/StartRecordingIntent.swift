//
//  StartRecordingIntent.swift
//  Memories
//

import AppIntents

struct StartRecordingIntent: AppIntent {
    static var title: LocalizedStringResource = "Start Recording"
    static var description: IntentDescription = "Start recording audio with Memories"
    static var openAppWhenRun = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let manager = await RecordingManager.shared

        if await manager.isRecording {
            return .result(dialog: "Memories is already recording.")
        }

        await manager.startRecording()
        return .result(dialog: "Recording started.")
    }
}
