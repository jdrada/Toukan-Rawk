//
//  APIConfig.swift
//  toukan
//

import Foundation

enum APIConfig {
    static let baseURL = URL(string: "http://23.20.135.83:8000")!
    static let uploadPath = "/upload"

    static var uploadURL: URL {
        baseURL.appendingPathComponent(uploadPath)
    }
}
