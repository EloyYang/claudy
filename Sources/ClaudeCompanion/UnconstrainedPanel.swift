import Cocoa
import SwiftUI

/// macOS의 자동 위치 제약(constrainFrameRect)을 무효화한 NSPanel.
/// 기본 NSPanel은 setFrameOrigin 호출 시 가시 영역 밖으로 나가지 못하도록
/// 내부적으로 위치를 보정하는데, 이를 우회해 메뉴바까지 자유롭게 이동할 수 있게 한다.
final class UnconstrainedPanel: NSPanel {
    // 채팅 입력이 활성화됐을 때 키보드 입력 허용
    override var canBecomeKey: Bool { true }

    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect {
        return frameRect
    }
}

/// ignoresMouseEvents 동적 제어와 함께 사용하는 NSHostingView 서브클래스.
/// hitTest는 기본 동작 그대로 유지 — 클릭 통과는 AppDelegate의 ignoresMouseEvents로 제어한다.
final class ClickThroughHostingView<T: View>: NSHostingView<T> {}
