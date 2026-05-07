import SwiftUI

struct RabbitCharacterView: View {
    @EnvironmentObject var ctrl: CompanionController
    @Environment(\.colorScheme) private var colorScheme

    private let p: CGFloat = 6.5

    private let bodyColor = Color(red: 0.91, green: 0.91, blue: 0.94)
    private let earPink   = Color(red: 0.95, green: 0.72, blue: 0.78)
    private let carrotCol = Color(red: 0.96, green: 0.55, blue: 0.18)
    private let leafCol   = Color(red: 0.28, green: 0.70, blue: 0.28)
    private let needleCol = Color(red: 0.52, green: 0.33, blue: 0.13)

    @State private var bodyDY:        CGFloat = 0
    @State private var bodyDX:        CGFloat = 0
    @State private var leftArmDY:     CGFloat = 0
    @State private var rightArmDY:    CGFloat = 0
    @State private var leftArmDX:     CGFloat = 0   // 뜨개질 시 팔을 안쪽으로
    @State private var rightArmDX:    CGFloat = 0
    @State private var earFoldScale:  CGFloat = 1.0
    @State private var hopPhase:      Bool    = false
    @State private var showCarrot:    Bool    = false
    @State private var showKnitting:  Bool    = false
    @State private var knittingPhase: Bool    = false
    @State private var blinking:      Bool    = false
    @State private var wideEyes:      Bool    = false
    @State private var eyeLookUp:     Bool    = false

    var body: some View {
        ZStack {
            // ── 귀 (머리 뒤)
            ZStack {
                px(w: 1.6, h: 3.4, c: bodyColor)
                px(w: 0.8, h: 2.7, c: earPink).offset(y: -p * 0.1)
            }
            .scaleEffect(x: 1, y: earFoldScale, anchor: .bottom)
            .animation(.spring(response: 0.28, dampingFraction: 0.45), value: earFoldScale)
            .offset(x: -p * 1.6, y: -p * 3.5 + bodyDY)

            ZStack {
                px(w: 1.6, h: 3.4, c: bodyColor)
                px(w: 0.8, h: 2.7, c: earPink).offset(y: -p * 0.1)
            }
            .scaleEffect(x: 1, y: earFoldScale, anchor: .bottom)
            .animation(.spring(response: 0.28, dampingFraction: 0.45), value: earFoldScale)
            .offset(x: p * 1.6, y: -p * 3.5 + bodyDY)

            // ── 몸통
            px(w: 4.5, h: 2.5, c: bodyColor).offset(y: p * 1.5 + bodyDY)

            // ── 왼팔 (뜨개질 시: 외곽선 표시 + 안쪽으로 이동)
            armView(outlined: showKnitting)
                .offset(x: -p * 2.65 + leftArmDX, y: p * 1.1 + leftArmDY + bodyDY)
                .animation(.easeInOut(duration: 0.32), value: leftArmDX)
                .animation(.easeInOut(duration: 0.28), value: leftArmDY)

            // ── 권한 요청 당근
            if showCarrot {
                carrotView
                    .offset(x: -p * 4.0, y: p * 0.1 + leftArmDY + bodyDY)
                    .animation(.easeOut(duration: 0.28), value: leftArmDY)
                    .transition(.scale(scale: 0.2, anchor: .bottom).combined(with: .opacity))
            }

            // ── 오른팔 (뜨개질 시: 외곽선 표시 + 안쪽으로 이동)
            armView(outlined: showKnitting)
                .offset(x: p * 2.65 + rightArmDX, y: p * 1.1 + rightArmDY + bodyDY)
                .animation(.easeInOut(duration: 0.32), value: rightArmDX)
                .animation(.easeInOut(duration: 0.28), value: rightArmDY)

            // ── 발
            px(w: 1.5, h: 0.9, c: bodyColor).offset(x: -p * 1.2, y: p * 2.9 + bodyDY)
            px(w: 1.5, h: 0.9, c: bodyColor).offset(x:  p * 1.2, y: p * 2.9 + bodyDY)

            // ── 뜨개질: 실뭉치 + 실 + 당근 + 바늘 (바늘은 팔과 독립적으로 배치)
            if showKnitting {
                // 실뭉치 (발 옆 바닥)
                yarnBallView
                    .offset(x: -p * 1.6, y: p * 3.15 + bodyDY)
                    .transition(.opacity)

                // 실 (실뭉치 → 당근): Shape 기반으로 ZStack 전체 프레임을 받아 중심 기준 좌표 사용
                YarnThreadShape(p: p)
                    .stroke(carrotCol.opacity(0.85), lineWidth: 1.0)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .allowsHitTesting(false)
                    .offset(y: bodyDY)
                    .transition(.opacity)

                // 당근 작업물 (고정)
                knittingWorkView
                    .offset(y: bodyDY)
                    .transition(.opacity)

                // 왼쪽 바늘 — 왼팔의 DX/DY를 그대로 따라감
                Rectangle()
                    .fill(needleCol)
                    .frame(width: p * 2.4, height: p * 0.27)
                    .rotationEffect(.degrees(24))
                    .offset(x: -p * 1.45 + leftArmDX,
                            y:  p * 1.3  + leftArmDY + bodyDY)
                    .animation(.easeInOut(duration: 0.28), value: leftArmDY)
                    .animation(.easeInOut(duration: 0.32), value: leftArmDX)
                    .transition(.opacity)

                // 오른쪽 바늘 — 오른팔의 DX/DY를 그대로 따라감
                Rectangle()
                    .fill(needleCol)
                    .frame(width: p * 2.4, height: p * 0.27)
                    .rotationEffect(.degrees(-24))
                    .offset(x:  p * 1.45 + rightArmDX,
                            y:  p * 1.3  + rightArmDY + bodyDY)
                    .animation(.easeInOut(duration: 0.28), value: rightArmDY)
                    .animation(.easeInOut(duration: 0.32), value: rightArmDX)
                    .transition(.opacity)
            }

            // ── 머리 (귀 앞, 뜨개질 작업물 앞)
            px(w: 5.5, h: 2.5, c: bodyColor).offset(y: -p * 0.8 + bodyDY)

            // ── 눈
            let eyeY = (eyeLookUp ? -p * 1.35 : -p * 0.9) + bodyDY
            eyeBlock(x: -p * 1.4, y: eyeY)
            eyeBlock(x:  p * 1.4, y: eyeY)

            // ── 코
            Rectangle()
                .fill(earPink)
                .frame(width: p * 0.55, height: p * 0.4)
                .offset(y: -p * 0.25 + bodyDY)
        }
        .offset(x: bodyDX)
        .animation(.easeInOut(duration: 0.20), value: bodyDX)
        .compositingGroup()
        .shadow(color: colorScheme == .light ? Color.black.opacity(0.30) : .clear,
                radius: 1.5, x: 0, y: 0)
        .onChange(of: ctrl.state)     { newState in applyAnimation(newState) }
        .onChange(of: ctrl.isSliding) { sliding in
            sliding ? startSlideHop() : stopSlideHop()
        }
        .onAppear {
            applyAnimation(ctrl.state)
            scheduleBlink()
        }
    }

    // MARK: – 팔 뷰 (뜨개질 중 외곽선으로 몸통과 구분)

    @ViewBuilder
    private func armView(outlined: Bool) -> some View {
        ZStack {
            if outlined {
                // 픽셀아트 스타일 테두리 — 몸통과 같은 색의 팔이 묻히지 않도록
                px(w: 1.9, h: 1.2, c: Color.black.opacity(0.22))
            }
            px(w: 1.5, h: 0.9, c: bodyColor)
        }
    }

    // MARK: – 권한 요청 당근 뷰

    private var carrotView: some View {
        ZStack {
            px(w: 1.5, h: 0.6, c: leafCol).offset(y: -p * 1.25)
            px(w: 0.7, h: 0.55, c: leafCol).offset(y: -p * 1.75)
            px(w: 0.7, h: 2.1, c: carrotCol)
        }
    }

    // MARK: – 뜨개질 작업물 (당근만, 바늘은 main ZStack에서 팔과 함께 관리)

    @ViewBuilder
    private var knittingWorkView: some View {
        ZStack {
            // 당근 잎
            px(w: 0.65, h: 0.55, c: leafCol).offset(x: -p * 0.35, y: p * 1.15)
            px(w: 0.65, h: 0.55, c: leafCol).offset(x:  p * 0.35, y: p * 1.15)
            px(w: 1.1,  h: 0.5,  c: leafCol).offset(y: p * 1.5)

            // 당근 몸통 (바늘 아래로 매달린 형태)
            px(w: 1.3, h: 1.1, c: carrotCol).offset(y: p * 2.1)
        }
    }

    // MARK: – 실뭉치 뷰

    private let yarnDark = Color(red: 0.82, green: 0.40, blue: 0.08)

    private var yarnBallView: some View {
        ZStack {
            // 몸통 원
            Circle()
                .fill(carrotCol)
                .frame(width: p * 1.7, height: p * 1.7)
            // 감긴 실 — 다양한 각도의 타원으로 실감나게
            ForEach([0.0, 40.0, 80.0, 130.0, 165.0, -40.0, -80.0], id: \.self) { angle in
                Ellipse()
                    .stroke(yarnDark.opacity(0.55), lineWidth: p * 0.15)
                    .frame(width: p * 1.45, height: p * 0.55)
                    .rotationEffect(.degrees(angle))
                    .clipShape(Circle().scale(0.92))
            }
            // 하이라이트
            Circle()
                .fill(Color.white.opacity(0.28))
                .frame(width: p * 0.48, height: p * 0.48)
                .offset(x: -p * 0.32, y: -p * 0.28)
            // 픽셀아트 테두리
            Circle()
                .stroke(Color.black.opacity(0.20), lineWidth: 0.8)
                .frame(width: p * 1.7, height: p * 1.7)
        }
    }

    // MARK: – 실 연결선 Shape (ZStack 프레임 전체를 받아 중심 기준으로 그림)

    // MARK: – 픽셀 블록 / 눈

    private func px(w: CGFloat, h: CGFloat, c: Color) -> some View {
        Rectangle().fill(c).frame(width: p * w, height: p * h)
    }

    @ViewBuilder
    private func eyeBlock(x: CGFloat, y: CGFloat) -> some View {
        Rectangle()
            .fill(Color.black)
            .frame(width:  p * 0.65,
                   height: blinking ? p * 0.12
                         : wideEyes ? p * 1.1
                         : p * 0.75)
            .offset(x: x, y: y)
            .animation(.easeInOut(duration: 0.08), value: blinking)
            .animation(.easeInOut(duration: 0.12), value: wideEyes)
            .animation(.easeInOut(duration: 0.25), value: eyeLookUp)
    }

    // MARK: – 상태별 애니메이션

    private func applyAnimation(_ state: CompanionState) {
        withAnimation(.easeOut(duration: 0.25)) {
            wideEyes  = false
            eyeLookUp = false
        }

        // 권한 상태가 아니면 팔·당근 내리기
        if case .permission = state { } else {
            withAnimation(.easeOut(duration: 0.25)) {
                showCarrot = false
            }
        }

        // 뜨개질 상태가 아니면 중지
        switch state {
        case .thinking, .toolUse: break
        default: stopKnitting()
        }

        if !ctrl.isSliding {
            withAnimation(.easeOut(duration: 0.2)) {
                bodyDY       = 0
                bodyDX       = 0
                earFoldScale = 1.0
            }
        }

        switch state {

        case .thinking, .toolUse:
            startKnitting()

        case .notification:
            withAnimation(.easeOut(duration: 0.12)) { bodyDY = -p * 2 }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.14) {
                withAnimation(.spring(response: 0.28, dampingFraction: 0.55)) { bodyDY = 0 }
            }

        case .permission:
            withAnimation(.easeInOut(duration: 0.18)) { wideEyes = true }
            withAnimation(.easeOut(duration: 0.28)) { leftArmDY = -p * 2.8 }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.20) {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.65)) {
                    showCarrot = true
                }
            }

        case .ready:
            scheduleIdleAnimation()

        case .idle:
            break
        }
    }

    // MARK: – 뜨개질 애니메이션

    private func startKnitting() {
        guard !showKnitting else { return }  // 이미 뜨개질 중이면 중복 시작 방지
        withAnimation(.easeOut(duration: 0.32)) {
            // 팔을 안쪽으로 모으고 살짝 올리기
            leftArmDX    =  p * 1.4
            rightArmDX   = -p * 1.4
            leftArmDY    = -p * 0.45
            rightArmDY   = -p * 0.45
            showKnitting = true
        }
        knittingPhase = false
        stepKnitting()
    }

    private func stepKnitting() {
        // 뜨개질 상태가 아니면 자동 중지
        switch ctrl.state {
        case .thinking, .toolUse: break
        default: return
        }

        knittingPhase.toggle()
        let base:  CGFloat = -p * 0.55
        let swing: CGFloat =  p * 0.38

        withAnimation(.easeInOut(duration: 0.32)) {
            leftArmDY  = knittingPhase ? base - swing : base + swing
            rightArmDY = knittingPhase ? base + swing : base - swing
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.36) {
            stepKnitting()
        }
    }

    private func stopKnitting() {
        withAnimation(.easeOut(duration: 0.25)) {
            showKnitting = false
            rightArmDY   = 0
            rightArmDX   = 0
            leftArmDX    = 0
        }
        // permission 상태가 아닐 때만 왼팔도 내리기
        if case .permission = ctrl.state { } else {
            withAnimation(.easeOut(duration: 0.25)) { leftArmDY = 0 }
        }
    }

    // MARK: – 아이들 애니메이션

    private func scheduleIdleAnimation() {
        let delay = Double.random(in: 6.0...13.0)
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
            guard case .ready = ctrl.state else { return }
            if Double.random(in: 0...1) < 0.5 {
                doIdleHop()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { scheduleIdleAnimation() }
            } else {
                doEarPerk()
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { scheduleIdleAnimation() }
            }
        }
    }

    private func doIdleHop() {
        guard case .ready = ctrl.state else { return }
        withAnimation(.easeOut(duration: 0.14)) { bodyDY = -p * 2.8 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
            guard case .ready = ctrl.state else { return }
            withAnimation(.spring(response: 0.28, dampingFraction: 0.52)) { bodyDY = 0 }
        }
    }

    private func doEarPerk() {
        guard case .ready = ctrl.state else { return }
        withAnimation(.easeIn(duration: 0.10)) { earFoldScale = 0.52 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.13) {
            guard case .ready = ctrl.state else {
                withAnimation(.easeOut(duration: 0.2)) { earFoldScale = 1.0 }
                return
            }
            withAnimation(.spring(response: 0.30, dampingFraction: 0.40)) { earFoldScale = 1.0 }
        }
    }

    // MARK: – 슬라이드

    private func startSlideHop() {
        hopPhase = false
        stepSlideHop()
    }

    private func stepSlideHop() {
        guard ctrl.isSliding else { stopSlideHop(); return }
        hopPhase.toggle()
        withAnimation(hopPhase
            ? .easeOut(duration: 0.11)
            : .spring(response: 0.18, dampingFraction: 0.52)) {
            bodyDY = hopPhase ? -p * 2.2 : 0
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.22) { stepSlideHop() }
    }

    private func stopSlideHop() {
        withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) { bodyDY = 0 }
    }

    // MARK: – 눈 깜빡임

    private func scheduleBlink() {
        DispatchQueue.main.asyncAfter(deadline: .now() + Double.random(in: 2.5...6.0)) {
            blinking = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.13) {
                blinking = false
                scheduleBlink()
            }
        }
    }
}

// MARK: - 실 연결선
// rect.midX/midY를 캐릭터 중심으로 삼아, 다른 뷰의 offset 좌표계와 일치하게 그린다.
struct YarnThreadShape: Shape {
    let p: CGFloat
    func path(in rect: CGRect) -> Path {
        let cx = rect.midX
        let cy = rect.midY
        var path = Path()
        path.move(to: CGPoint(x: cx - p * 1.6, y: cy + p * 2.3))   // 실뭉치 상단
        path.addQuadCurve(
            to:      CGPoint(x: cx,           y: cy + p * 2.65),    // 당근 하단 근처
            control: CGPoint(x: cx - p * 0.7, y: cy + p * 2.85)    // 자연스러운 처짐
        )
        return path
    }
}
