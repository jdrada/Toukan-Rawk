//
//  ContentView.swift
//  toukan
//

import SwiftUI
import SwiftData

struct ContentView: View {
    var recordingManager: RecordingManager
    var uploadManager: UploadManager

    var body: some View {
        TabView {
            Tab("Record", systemImage: "mic.fill") {
                RecordingView(
                    recordingManager: recordingManager,
                    uploadManager: uploadManager
                )
            }

            Tab("Memories", systemImage: "list.bullet") {
                NavigationStack {
                    MemoriesListView(uploadManager: uploadManager)
                }
            }
        }
    }
}

#Preview {
    ContentView(
        recordingManager: RecordingManager.shared,
        uploadManager: UploadManager.shared
    )
    .modelContainer(for: Recording.self, inMemory: true)
}
