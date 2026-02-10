//
//  Recording.swift
//  toukan
//

import Foundation
import SwiftData

enum UploadStatus: String, Codable {
    case pending
    case uploading
    case uploaded
    case failed
}

@Model
final class Recording {
    var id: UUID
    var filePath: String
    var recordedAt: Date
    var duration: TimeInterval
    var uploadStatusRaw: String
    var memoryId: String?
    var retryCount: Int
    var lastAttempt: Date?

    var uploadStatus: UploadStatus {
        get { UploadStatus(rawValue: uploadStatusRaw) ?? .pending }
        set { uploadStatusRaw = newValue.rawValue }
    }

    init(
        id: UUID = UUID(),
        filePath: String,
        recordedAt: Date = Date(),
        duration: TimeInterval = 0,
        uploadStatus: UploadStatus = .pending,
        memoryId: String? = nil,
        retryCount: Int = 0,
        lastAttempt: Date? = nil
    ) {
        self.id = id
        self.filePath = filePath
        self.recordedAt = recordedAt
        self.duration = duration
        self.uploadStatusRaw = uploadStatus.rawValue
        self.memoryId = memoryId
        self.retryCount = retryCount
        self.lastAttempt = lastAttempt
    }
}
