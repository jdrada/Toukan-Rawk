//
//  StartRecordingIntent.swift
//  toukan
//

import AppIntents

struct StartRecordingIntent: AppIntent {
    static var title: LocalizedStringResource = "Start Recording"
    static var description: IntentDescription = "Start recording audio with Toukan"
    static var openAppWhenRun = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let manager = await RecordingManager.shared

        if await manager.isRecording {
            return .result(dialog: "Toukan is already recording.")
        }

        await manager.startRecording()
        return .result(dialog: "Recording started.")
    }
}
