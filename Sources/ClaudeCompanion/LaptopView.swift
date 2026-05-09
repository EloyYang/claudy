import SwiftUI

/// 생각중/쓰기 도구 사용 시 — 다리 위 맥북 측면 타이핑 뷰
/// 구도: 살짝 측면에서 본 각도, 다리 위에 올려둔 느낌, 책상 없음
struct LaptopView: View {
    let p:      CGFloat
    let bodyDY: CGFloat

    private let silverCol  = Color(red: 0.76, green: 0.76, blue: 0.80)
    private let silverHi   = Color(red: 0.88, green: 0.88, blue: 0.92)
    private let silverDark = Color(red: 0.50, green: 0.50, blue: 0.54)
    private let silverMid  = Color(red: 0.64, green: 0.64, blue: 0.68)
    private let appleCol   = Color(red: 0.92, green: 0.92, blue: 0.95)

    var body: some View {
        ZStack {
            laptopBody
        }
        .offset(y: bodyDY)
    }

    private var laptopBody: some View {
        ZStack {
            // ── 뚜껑 뒷면 메인 (Apple 로고 있는 면)
            rect(w: 3.15, h: 2.15, c: silverCol)
                .offset(y: p * 1.48)

            // ── 뚜껑 상단 엣지 하이라이트
            rect(w: 3.15, h: 0.17, c: silverHi)
                .offset(y: p * 0.41)

            // ── 뚜껑 좌우 엣지
            rect(w: 0.12, h: 2.15, c: silverDark.opacity(0.40))
                .offset(x: -p * 1.52, y: p * 1.48)
            rect(w: 0.12, h: 2.15, c: silverDark.opacity(0.25))
                .offset(x: p * 1.52, y: p * 1.48)

            // ── Apple 로고 (뚜껑 중앙)
            appleLogoView
                .offset(y: p * 1.42)

            // ── 힌지
            rect(w: 3.50, h: 0.20, c: silverDark)
                .offset(y: p * 2.64)

            // ── 키보드 베이스 (뚜껑보다 살짝 넓어 원근감)
            rect(w: 3.80, h: 0.44, c: silverMid)
                .offset(y: p * 2.90)

            // ── 키보드 베이스 앞면 두께 (측면 시점 입체감)
            rect(w: 3.80, h: 0.16, c: silverDark)
                .offset(y: p * 3.13)

            // ── 키 배열 힌트
            rect(w: 3.10, h: 0.13, c: silverDark.opacity(0.32))
                .offset(y: p * 2.82)

            // ── 트랙패드
            rect(w: 1.0, h: 0.22, c: silverDark.opacity(0.20))
                .offset(y: p * 3.02)
        }
    }

    // MARK: - Apple 로고 (픽셀아트)

    private var appleLogoView: some View {
        ZStack {
            // 줄기
            rect(w: 0.13, h: 0.22, c: appleCol)
                .offset(x: p * 0.06, y: -p * 0.52)
            // 잎
            rect(w: 0.28, h: 0.15, c: appleCol)
                .rotationEffect(.degrees(-28))
                .offset(x: p * 0.20, y: -p * 0.50)
            // 사과 상단
            rect(w: 0.54, h: 0.32, c: appleCol)
                .offset(y: -p * 0.20)
            // 사과 중간 (가장 넓음)
            rect(w: 0.70, h: 0.36, c: appleCol)
                .offset(y:  p * 0.08)
            // 사과 하단
            rect(w: 0.54, h: 0.27, c: appleCol)
                .offset(y:  p * 0.38)
            // 한 입 베어먹은 자국
            rect(w: 0.22, h: 0.20, c: silverCol)
                .offset(x: p * 0.24, y: -p * 0.28)
        }
    }

    private func rect(w: CGFloat, h: CGFloat, c: Color) -> some View {
        Rectangle().fill(c).frame(width: p * w, height: p * h)
    }
}
