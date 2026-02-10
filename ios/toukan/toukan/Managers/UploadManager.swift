//
//  UploadManager.swift
//  toukan
//

import Foundation
import Network
import Observation
import SwiftData

@Observable
final class UploadManager: NSObject {
    static let shared = UploadManager()

    var isConnected = true

    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "com.toukan.networkMonitor")
    private var backgroundSession: URLSession!
    private var modelContainer: ModelContainer?
    private var uploadCompletionHandlers: [String: (URL?, URLResponse?, (any Error)?) -> Void] = [:]

    private static let maxRetries = 5
    private static let sessionIdentifier = "com.toukan.backgroundUpload"

    private override init() {
        super.init()
        let config = URLSessionConfiguration.background(withIdentifier: Self.sessionIdentifier)
        config.isDiscretionary = false
        config.sessionSendsLaunchEvents = true
        backgroundSession = URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }

    func configure(with container: ModelContainer) {
        modelContainer = container
    }

    // MARK: - Connectivity Monitoring

    func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            let connected = path.status == .satisfied
            Task { @MainActor in
                self?.isConnected = connected
                if connected {
                    self?.retryPendingUploads()
                }
            }
        }
        monitor.start(queue: monitorQueue)
    }

    func stopMonitoring() {
        monitor.cancel()
    }

    // MARK: - Upload

    func enqueueUpload(for recording: Recording, in context: ModelContext) {
        recording.uploadStatus = .pending
        try? context.save()

        guard isConnected else { return }
        performUpload(recordingId: recording.id, filePath: recording.filePath)
    }

    func retryPendingUploads() {
        guard let container = modelContainer else { return }

        Task { @MainActor in
            let context = ModelContext(container)
            let pendingRaw = UploadStatus.pending.rawValue
            let failedRaw = UploadStatus.failed.rawValue
            let predicate = #Predicate<Recording> { recording in
                recording.uploadStatusRaw == pendingRaw || recording.uploadStatusRaw == failedRaw
            }
            let descriptor = FetchDescriptor<Recording>(predicate: predicate)

            guard let recordings = try? context.fetch(descriptor) else { return }
            for recording in recordings where recording.retryCount < Self.maxRetries {
                performUpload(recordingId: recording.id, filePath: recording.filePath)
            }
        }
    }

    private func performUpload(recordingId: UUID, filePath: String) {
        let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let fileURL = documentsURL.appendingPathComponent(filePath)

        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            print("❌ Upload failed: File not found at \(fileURL.path)")
            markRecording(id: recordingId, status: .failed)
            return
        }

        print("📤 Starting upload to: \(APIConfig.uploadURL)")
        
        // Build multipart form data and write to temp file for background upload
        let boundary = UUID().uuidString
        var request = URLRequest(url: APIConfig.uploadURL)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30

        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".tmp")
        do {
            let bodyData = try buildMultipartBody(fileURL: fileURL, boundary: boundary)
            try bodyData.write(to: tempURL)
        } catch {
            markRecording(id: recordingId, status: .failed)
            return
        }

        let task = backgroundSession.uploadTask(with: request, fromFile: tempURL)
        task.taskDescription = recordingId.uuidString
        task.resume()

        markRecording(id: recordingId, status: .uploading)
    }

    private func buildMultipartBody(fileURL: URL, boundary: String) throws -> Data {
        var body = Data()
        let filename = fileURL.lastPathComponent
        let mimeType = "audio/mp4"

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(try Data(contentsOf: fileURL))
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        return body
    }

    // MARK: - Status Updates

    private func markRecording(id: UUID, status: UploadStatus, memoryId: String? = nil) {
        guard let container = modelContainer else { return }

        Task { @MainActor in
            let context = ModelContext(container)
            let predicate = #Predicate<Recording> { $0.id == id }
            let descriptor = FetchDescriptor<Recording>(predicate: predicate)

            guard let recording = try? context.fetch(descriptor).first else { return }
            recording.uploadStatus = status
            if let memoryId {
                recording.memoryId = memoryId
            }
            if status == .failed {
                recording.retryCount += 1
                recording.lastAttempt = Date()
            }
            try? context.save()
        }
    }
}

// MARK: - URLSessionDataDelegate

extension UploadManager: URLSessionDataDelegate {
    nonisolated func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: (any Error)?
    ) {
        guard let recordingIdString = task.taskDescription,
              let recordingId = UUID(uuidString: recordingIdString) else { return }

        if let error {
            print("❌ Upload failed with error: \(error.localizedDescription)")
            Task {
                await markRecording(id: recordingId, status: .failed)
                await scheduleRetry(for: recordingId)
            }
            return
        }

        guard let httpResponse = task.response as? HTTPURLResponse else {
            print("❌ Upload failed: No HTTP response")
            Task {
                await markRecording(id: recordingId, status: .failed)
                await scheduleRetry(for: recordingId)
            }
            return
        }

        if (200...299).contains(httpResponse.statusCode) {
            print("✅ Upload successful! Status: \(httpResponse.statusCode)")
            // For background sessions, try to get response data if available
            // If not available, mark as uploaded anyway
            Task {
                await markRecording(id: recordingId, status: .uploaded)
            }
        } else {
            print("❌ Upload failed with status code: \(httpResponse.statusCode)")
            Task {
                await markRecording(id: recordingId, status: .failed)
                await scheduleRetry(for: recordingId)
            }
        }
    }

    // Note: didReceive data is NOT called for background upload tasks
    // Background sessions only support task completion callbacks

    nonisolated func urlSessionDidFinishEvents(forBackgroundURLSession session: URLSession) {
        // Called when all background tasks are complete
    }

    // MARK: - Retry

    private func scheduleRetry(for recordingId: UUID) {
        guard let container = modelContainer else { return }

        Task { @MainActor in
            let context = ModelContext(container)
            let predicate = #Predicate<Recording> { $0.id == recordingId }
            let descriptor = FetchDescriptor<Recording>(predicate: predicate)

            guard let recording = try? context.fetch(descriptor).first else { return }
            guard recording.retryCount < Self.maxRetries else { return }

            let delay = pow(2.0, Double(recording.retryCount))
            try? await Task.sleep(for: .seconds(delay))
            performUpload(recordingId: recordingId, filePath: recording.filePath)
        }
    }
}
