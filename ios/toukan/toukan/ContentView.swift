//
//  ContentView.swift
//  toukan
//

import SwiftUI
import SwiftData

struct ContentView: View {
    var body: some View {
        NavigationStack {
            Text("Toukan")
                .font(.largeTitle)
                .fontWeight(.bold)
        }
    }
}

#Preview {
    ContentView()
        .modelContainer(for: Recording.self, inMemory: true)
}
