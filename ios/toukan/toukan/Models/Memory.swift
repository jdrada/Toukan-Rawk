//
//  Memory.swift
//  toukan
//

import Foundation

/// Status of a memory in the processing pipeline
enum MemoryStatus: String, Codable {
    case uploading
    case processing
    case ready
    case failed
}

/// Represents a memory fetched from the backend API
struct Memory: Codable, Identifiable {
    let id: String
    let title: String?
    let status: MemoryStatus
    let audioUrl: String
    let transcript: String?
    let summary: String?
    let keyPoints: [String]?
    let actionItems: [String]?
    let duration: Double?
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case status
        case audioUrl = "audio_url"
        case transcript
        case summary
        case keyPoints = "key_points"
        case actionItems = "action_items"
        case duration
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    /// UUID computed property for Identifiable conformance
    var uuid: UUID {
        UUID(uuidString: id) ?? UUID()
    }
}

/// Paginated response from the memories list endpoint
struct MemoryListResponse: Codable {
    let items: [Memory]
    let total: Int
    let page: Int
    let pageSize: Int
    let hasNext: Bool

    enum CodingKeys: String, CodingKey {
        case items
        case total
        case page
        case pageSize = "page_size"
        case hasNext = "has_next"
    }
}
