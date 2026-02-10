//
//  MemoriesShortcuts.swift
//  Memories
//

import AppIntents

struct MemoriesShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: StartRecordingIntent(),
            phrases: [
                "Start recording with \(.applicationName)",
                "Record with \(.applicationName)",
                "\(.applicationName) start listening",
            ],
            shortTitle: "Start Recording",
            systemImageName: "mic.fill"
        )

        AppShortcut(
            intent: StopRecordingIntent(),
            phrases: [
                "Stop recording with \(.applicationName)",
                "\(.applicationName) stop listening",
                "Stop \(.applicationName)",
            ],
            shortTitle: "Stop Recording",
            systemImageName: "stop.circle.fill"
        )
    }
}
