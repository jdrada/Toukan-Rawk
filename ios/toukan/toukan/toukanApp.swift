//
//  toukanApp.swift
//  toukan
//

import SwiftUI
import SwiftData

@main
struct toukanApp: App {
    let recordingManager = RecordingManager.shared
    let uploadManager = UploadManager.shared

    var sharedModelContainer: ModelContainer = {
        let schema = Schema([
            Recording.self,
        ])
        let modelConfiguration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)

        do {
            return try ModelContainer(for: schema, configurations: [modelConfiguration])
        } catch {
            fatalError("Could not create ModelContainer: \(error)")
        }
    }()

    var body: some Scene {
        WindowGroup {
            ContentView(
                recordingManager: recordingManager,
                uploadManager: uploadManager
            )
            .onAppear {
                uploadManager.configure(with: sharedModelContainer)
                uploadManager.startMonitoring()
                uploadManager.retryPendingUploads()
            }
        }
        .modelContainer(sharedModelContainer)
    }
}
