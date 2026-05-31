import Foundation
import Network

/// SSH Remote 환경에서 훅 스크립트가 보내는 이벤트를 수신하는 로컬 TCP 서버.
/// 수신한 이벤트를 /tmp/claude-companion-events-{sessionId}.jsonl 파일에 기록해
/// 기존 세션 스캐너가 자동으로 감지하게 한다.
///
/// 사용법 (SSH 설정):
///   ~/.ssh/config 에 다음 추가:
///     Host <원격서버>
///       RemoteForward 58765 localhost:58765
final class EventSocketServer {

    static let port: UInt16 = 58765

    /// 새 세션 파일이 생성/갱신됐을 때 호출 — (sessionId, fileURL)
    var onNewSession: ((String, URL) -> Void)?

    private var listener: NWListener?

    // MARK: - Lifecycle

    func start() {
        guard let port = NWEndpoint.Port(rawValue: Self.port) else { return }
        let params = NWParameters.tcp
        params.allowLocalEndpointReuse = true
        guard let l = try? NWListener(using: params, on: port) else { return }
        l.stateUpdateHandler = { _ in }
        l.newConnectionHandler = { [weak self] conn in self?.handle(conn) }
        l.start(queue: .global(qos: .background))
        self.listener = l
    }

    func stop() {
        listener?.cancel()
        listener = nil
    }

    // MARK: - Connection handling

    private func handle(_ conn: NWConnection) {
        conn.start(queue: .global(qos: .background))
        var buf = Data()

        func recv() {
            conn.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [self] data, _, done, _ in
                if let d = data { buf.append(d) }
                if done { process(buf); conn.cancel() }
                else     { recv() }
            }
        }
        recv()
    }

    private func process(_ data: Data) {
        guard let text = String(data: data, encoding: .utf8) else { return }
        for raw in text.components(separatedBy: "\n") {
            let line = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !line.isEmpty,
                  let jd  = line.data(using: .utf8),
                  let ev  = try? JSONSerialization.jsonObject(with: jd) as? [String: Any],
                  let sid = ev["session_id"] as? String, !sid.isEmpty else { continue }

            // 파일명에 안전한 문자만 허용
            let safeSid = sid.filter { $0.isLetter || $0.isNumber || $0 == "-" || $0 == "_" }
            guard !safeSid.isEmpty else { continue }

            let path = "/tmp/claude-companion-events-\(safeSid).jsonl"
            appendLine(line, to: path)
            onNewSession?(safeSid, URL(fileURLWithPath: path))
        }
    }

    private func appendLine(_ line: String, to path: String) {
        guard let bytes = (line + "\n").data(using: .utf8) else { return }
        let fm = FileManager.default
        if fm.fileExists(atPath: path) {
            guard let fh = FileHandle(forWritingAtPath: path) else { return }
            fh.seekToEndOfFile()
            fh.write(bytes)
            try? fh.close()
        } else {
            fm.createFile(atPath: path, contents: bytes)
        }
    }
}
