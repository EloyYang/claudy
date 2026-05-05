import Foundation
import AppKit

final class UpdateChecker {
    private static let apiURL = "https://api.github.com/repos/EloyYang/buni/releases/latest"
    private static let releasePage = "https://github.com/EloyYang/buni/releases/latest"

    /// 앱 번들에서 현재 버전 읽기
    static var currentVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
    }

    /// GitHub API로 최신 릴리즈 버전 확인.
    /// 새 버전이 있으면 버전 문자열("1.2.3")을 completion에 전달, 없으면 nil.
    static func check(completion: @escaping (String?) -> Void) {
        guard let url = URL(string: apiURL) else { return }
        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData)
        req.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")

        URLSession.shared.dataTask(with: req) { data, _, _ in
            guard let data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let tag  = json["tag_name"] as? String else {
                DispatchQueue.main.async { completion(nil) }
                return
            }
            let latest  = tag.hasPrefix("v") ? String(tag.dropFirst()) : tag
            let current = currentVersion
            let newer   = latest.compare(current, options: .numeric) == .orderedDescending
            DispatchQueue.main.async { completion(newer ? latest : nil) }
        }.resume()
    }

    static func openReleasePage() {
        NSWorkspace.shared.open(URL(string: releasePage)!)
    }
}
