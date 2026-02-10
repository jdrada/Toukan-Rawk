//
//  MemoryAPIClient.swift
//  toukan
//

import Foundation

/// Error type for MemoryAPIClient operations
enum MemoryAPIError: LocalizedError {
    case invalidURL
    case badServerResponse(statusCode: Int, body: String)
    case decodingFailed(Error, rawResponse: String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL for memory API request"
        case .badServerResponse(let statusCode, let body):
            return "Server returned status code \(statusCode): \(body)"
        case .decodingFailed(let error, let rawResponse):
            return "Failed to decode API response: \(error.localizedDescription)\nRaw response: \(rawResponse)"
        }
    }
}

/// Client for fetching memories from the backend API
enum MemoryAPIClient {
    private static let baseURL = APIConfig.baseURL

    /// Fetches a paginated list of memories from the backend
    static func fetchMemories(page: Int = 1, pageSize: Int = 50) async throws -> MemoryListResponse {
        var components = URLComponents(url: baseURL.appendingPathComponent("/memories"), resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "page", value: String(page)),
            URLQueryItem(name: "page_size", value: String(pageSize))
        ]

        guard let url = components.url else {
            throw MemoryAPIError.invalidURL
        }

        print("[MemoryAPIClient] Fetching memories from: \(url.absoluteString)")

        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        print("[MemoryAPIClient] Received response with status code: \(httpResponse.statusCode)")

        guard httpResponse.statusCode == 200 else {
            let responseBody = String(data: data, encoding: .utf8) ?? "<unable to decode response>"
            print("[MemoryAPIClient] Error response: \(responseBody)")
            throw MemoryAPIError.badServerResponse(statusCode: httpResponse.statusCode, body: responseBody)
        }

        // Log raw response for debugging
        if let rawResponse = String(data: data, encoding: .utf8) {
            print("[MemoryAPIClient] Raw response: \(rawResponse)")
        }

        let decoder = JSONDecoder()
        // Note: We use custom CodingKeys in models, so we use default key strategy
        
        // Custom date decoder to handle ISO8601 dates with variable fractional seconds
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            
            // Use DateFormatter for flexible fractional seconds parsing
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.timeZone = TimeZone(secondsFromGMT: 0)
            
            // Try with fractional seconds (supports any number of decimal places)
            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
            if let date = formatter.date(from: dateString) {
                return date
            }
            
            // Fallback: Try without fractional seconds
            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
            if let date = formatter.date(from: dateString) {
                return date
            }
            
            // Fallback: Try standard ISO8601 with Z
            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ssZ"
            if let date = formatter.date(from: dateString) {
                return date
            }
            
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date string \(dateString)"
            )
        }

        do {
            let result = try decoder.decode(MemoryListResponse.self, from: data)
            print("[MemoryAPIClient] Successfully decoded \(result.items.count) memories")
            return result
        } catch {
            let rawResponse = String(data: data, encoding: .utf8) ?? "<unable to decode response>"
            print("[MemoryAPIClient] Decoding error: \(error)")
            throw MemoryAPIError.decodingFailed(error, rawResponse: rawResponse)
        }
    }
}
