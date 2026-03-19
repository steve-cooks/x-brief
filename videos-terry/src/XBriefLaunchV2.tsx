import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  Img,
  staticFile,
} from "remotion";

// ─── Design Tokens ───────────────────────────────────────────────────────────

const COLORS = {
  bg: "#08080C",
  bgSubtle: "#12121A",
  text: "#F5F5F7",
  textSecondary: "#8E8E93",
  accent: "#00D4FF",
  warm: "#FF6B35",
  glowAccent: "rgba(0, 212, 255, 0.08)",
};

const FONTS = {
  heading: "'SF Pro Display', 'Helvetica Neue', sans-serif",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

const clamp = (
  v: number,
  input: [number, number],
  output: [number, number],
) =>
  interpolate(v, input, output, {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** Blur-in + translateY + opacity entrance */
const BlurIn: React.FC<{
  children: React.ReactNode;
  delay?: number;
  duration?: number;
}> = ({ children, delay = 0, duration = 45 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({
    fps,
    frame,
    config: { damping: 22 },
    delay,
    durationInFrames: duration,
  });
  return (
    <div
      style={{
        filter: `blur(${interpolate(progress, [0, 1], [15, 0])}px)`,
        transform: `translateY(${interpolate(progress, [0, 1], [20, 0])}px)`,
        opacity: interpolate(progress, [0, 0.4, 1], [0, 0.7, 1]),
      }}
    >
      {children}
    </div>
  );
};

/** Shared fade-out at end of a scene */
const useFadeOut = (startFrame: number, endFrame: number) => {
  const frame = useCurrentFrame();
  const opacity = clamp(frame, [startFrame, endFrame], [1, 0]);
  const blur = clamp(frame, [startFrame, endFrame], [0, 10]);
  return { opacity, blur };
};

// ─── Background ──────────────────────────────────────────────────────────────

const Background: React.FC = () => (
  <AbsoluteFill>
    {/* Base */}
    <AbsoluteFill style={{ background: COLORS.bg }} />
    {/* Radial gradient */}
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 45%, ${COLORS.bgSubtle} 0%, ${COLORS.bg} 70%)`,
      }}
    />
    {/* Noise overlay */}
    <AbsoluteFill
      style={{
        opacity: 0.025,
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        backgroundSize: "256px 256px",
      }}
    />
    {/* Vignette */}
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.55) 100%)",
      }}
    />
  </AbsoluteFill>
);

// ─── Scene 1: The Hook (frames 0-240) ───────────────────────────────────────

const SceneTheHook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const { opacity: fadeOutOpacity, blur: fadeOutBlur } = useFadeOut(215, 240);

  // "2 hours" entrance
  const twoHoursIn = spring({
    fps,
    frame,
    config: { damping: 22 },
    delay: 10,
    durationInFrames: 40,
  });
  const twoHoursBlur = interpolate(twoHoursIn, [0, 1], [15, 0]);
  const twoHoursY = interpolate(twoHoursIn, [0, 1], [20, 0]);
  const twoHoursOpacity = interpolate(
    twoHoursIn,
    [0, 0.4, 1],
    [0, 0.7, 1],
  );

  // Strikethrough animation: starts at frame 80, completes by frame 110
  const strikeProgress = clamp(frame, [80, 110], [0, 1]);
  const strikeWidth = `${strikeProgress * 100}%`;

  // "5 minutes" entrance (after strikethrough)
  const fiveMinIn = spring({
    fps,
    frame,
    config: { damping: 22 },
    delay: 100,
    durationInFrames: 45,
  });
  const fiveMinBlur = interpolate(fiveMinIn, [0, 1], [15, 0]);
  const fiveMinY = interpolate(fiveMinIn, [0, 1], [25, 0]);
  const fiveMinOpacity = interpolate(fiveMinIn, [0, 0.4, 1], [0, 0.7, 1]);

  // Subtle warm glow behind "2 hours"
  const warmGlow = interpolate(
    Math.sin(frame * 0.04),
    [-1, 1],
    [0.04, 0.1],
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOutOpacity,
        filter: `blur(${fadeOutBlur}px)`,
      }}
    >
      {/* Warm glow */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: COLORS.warm,
          filter: "blur(180px)",
          opacity: warmGlow,
          top: "25%",
        }}
      />

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
        }}
      >
        {/* "2 hours" with strikethrough */}
        <div
          style={{
            position: "relative",
            opacity: twoHoursOpacity,
            filter: `blur(${twoHoursBlur}px)`,
            transform: `translateY(${twoHoursY}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 120,
              fontWeight: 800,
              color: COLORS.warm,
              letterSpacing: -5,
              lineHeight: 1.1,
            }}
          >
            2 hours
          </div>
          {/* Strikethrough line */}
          <div
            style={{
              position: "absolute",
              top: "52%",
              left: "-4%",
              width: strikeWidth,
              maxWidth: "108%",
              height: 6,
              background: COLORS.text,
              borderRadius: 3,
              opacity: strikeProgress > 0 ? 0.9 : 0,
            }}
          />
        </div>

        {/* "5 minutes" */}
        <div
          style={{
            opacity: fiveMinOpacity,
            filter: `blur(${fiveMinBlur}px)`,
            transform: `translateY(${fiveMinY}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 120,
              fontWeight: 800,
              color: COLORS.accent,
              letterSpacing: -5,
              lineHeight: 1.1,
            }}
          >
            5 minutes
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Scene 2: The Promise (frames 240-480) ──────────────────────────────────

const SceneThePromise: React.FC = () => {
  const frame = useCurrentFrame();
  const { opacity: fadeOutOpacity, blur: fadeOutBlur } = useFadeOut(215, 240);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOutOpacity,
        filter: `blur(${fadeOutBlur}px)`,
      }}
    >
      {/* Subtle accent glow */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 400,
          borderRadius: "50%",
          background: COLORS.accent,
          filter: "blur(200px)",
          opacity: 0.06,
        }}
      />

      <BlurIn delay={15} duration={50}>
        <div
          style={{
            fontFamily: FONTS.heading,
            fontSize: 72,
            fontWeight: 800,
            color: COLORS.text,
            textAlign: "center",
            lineHeight: 1.25,
            letterSpacing: -3,
            maxWidth: 1100,
          }}
        >
          <span style={{ color: COLORS.accent }}>One sentence</span>
          <br />
          catches you up on everything
        </div>
      </BlurIn>
    </AbsoluteFill>
  );
};

// ─── Phone Mockup Component ─────────────────────────────────────────────────

const PhoneMockup: React.FC<{
  imageSrc: string;
  width: number;
  height: number;
  style?: React.CSSProperties;
}> = ({ imageSrc, width, height, style }) => (
  <div
    style={{
      width,
      height,
      borderRadius: 40,
      border: "2px solid rgba(255,255,255,0.12)",
      overflow: "hidden",
      boxShadow: `0 0 120px rgba(0, 212, 255, 0.1), 0 40px 80px rgba(0,0,0,0.5)`,
      flexShrink: 0,
      ...style,
    }}
  >
    <Img
      src={staticFile(imageSrc)}
      style={{
        width: "100%",
        height: "100%",
        objectFit: "cover",
        objectPosition: "top",
      }}
    />
  </div>
);

// ─── Scene 3: The Hero — TL;DR Screenshot (frames 480-840) ─────────────────

const SceneTheHero: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const { opacity: fadeOutOpacity, blur: fadeOutBlur } = useFadeOut(335, 360);

  // Phone entrance: scale up + blur clear
  const phoneIn = spring({
    fps,
    frame,
    config: { damping: 20 },
    delay: 10,
    durationInFrames: 50,
  });
  const phoneScale = interpolate(phoneIn, [0, 1], [0.92, 1]);
  const phoneBlur = interpolate(phoneIn, [0, 1], [8, 0]);
  const phoneOpacity = interpolate(phoneIn, [0, 0.3, 1], [0, 0.6, 1]);

  // Label entrance
  const labelIn = spring({
    fps,
    frame,
    config: { damping: 22 },
    delay: 40,
    durationInFrames: 40,
  });

  // Soft glow pulse behind phone
  const glowPulse = interpolate(
    Math.sin(frame * 0.03),
    [-1, 1],
    [0.06, 0.12],
  );

  const PHONE_W = 380;
  const PHONE_H = 680;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOutOpacity,
        filter: `blur(${fadeOutBlur}px)`,
      }}
    >
      {/* Radial glow behind phone */}
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 700,
          borderRadius: "50%",
          background: COLORS.accent,
          filter: "blur(160px)",
          opacity: glowPulse,
        }}
      />

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
        }}
      >
        {/* TL;DR label */}
        <div
          style={{
            fontFamily: FONTS.heading,
            fontSize: 28,
            fontWeight: 600,
            color: COLORS.accent,
            letterSpacing: 4,
            textTransform: "uppercase",
            opacity: interpolate(labelIn, [0, 1], [0, 1]),
            filter: `blur(${interpolate(labelIn, [0, 1], [10, 0])}px)`,
            transform: `translateY(${interpolate(labelIn, [0, 1], [10, 0])}px)`,
          }}
        >
          TL;DR
        </div>

        {/* Phone */}
        <div
          style={{
            opacity: phoneOpacity,
            filter: `blur(${phoneBlur}px)`,
            transform: `scale(${phoneScale})`,
          }}
        >
          <PhoneMockup
            imageSrc="tldr-tab.png"
            width={PHONE_W}
            height={PHONE_H}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Scene 4: Quick Flash — Other Tabs (frames 840-960) ────────────────────

const SceneQuickFlash: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const { opacity: fadeOutOpacity, blur: fadeOutBlur } = useFadeOut(100, 120);

  // For You phone entrance (left)
  const forYouIn = spring({
    fps,
    frame,
    config: { damping: 18 },
    delay: 5,
    durationInFrames: 35,
  });

  // Following phone entrance (right)
  const followingIn = spring({
    fps,
    frame,
    config: { damping: 18 },
    delay: 20,
    durationInFrames: 35,
  });

  const PHONE_W = 290;
  const PHONE_H = 520;

  const makePhoneStyle = (
    progress: number,
    offsetX: number,
  ): React.CSSProperties => ({
    opacity: interpolate(progress, [0, 0.3, 1], [0, 0.6, 1]),
    filter: `blur(${interpolate(progress, [0, 1], [8, 0])}px)`,
    transform: `scale(${interpolate(progress, [0, 1], [0.92, 1])}) translateX(${offsetX}px)`,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 20,
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOutOpacity,
        filter: `blur(${fadeOutBlur}px)`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 80,
        }}
      >
        {/* For You */}
        <div style={makePhoneStyle(forYouIn, 0)}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 24,
              fontWeight: 600,
              color: COLORS.accent,
              letterSpacing: 3,
              textTransform: "uppercase",
            }}
          >
            For You
          </div>
          <PhoneMockup
            imageSrc="foryou-tab.png"
            width={PHONE_W}
            height={PHONE_H}
          />
        </div>

        {/* Following */}
        <div style={makePhoneStyle(followingIn, 0)}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 24,
              fontWeight: 600,
              color: COLORS.accent,
              letterSpacing: 3,
              textTransform: "uppercase",
            }}
          >
            Following
          </div>
          <PhoneMockup
            imageSrc="following-tab.png"
            width={PHONE_W}
            height={PHONE_H}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Scene 5: The Closer (frames 960-1200) ──────────────────────────────────

const SceneTheCloser: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Subtle accent glow
  const glowOpacity = interpolate(
    Math.sin(frame * 0.04),
    [-1, 1],
    [0.04, 0.08],
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* Glow */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: COLORS.accent,
          filter: "blur(180px)",
          opacity: glowOpacity,
        }}
      />

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
        }}
      >
        {/* Main tagline */}
        <BlurIn delay={5} duration={45}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 72,
              fontWeight: 800,
              color: COLORS.text,
              textAlign: "center",
              letterSpacing: -3,
              lineHeight: 1.2,
              maxWidth: 1000,
            }}
          >
            An AI reads X
            <br />
            so you don't have to
          </div>
        </BlurIn>

        {/* Open source line */}
        <BlurIn delay={35} duration={40}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 30,
              fontWeight: 500,
              color: COLORS.textSecondary,
              marginTop: 12,
              letterSpacing: 1,
            }}
          >
            Open source. Free.
          </div>
        </BlurIn>

        {/* GitHub link */}
        <BlurIn delay={55} duration={40}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 28,
              fontWeight: 600,
              color: COLORS.accent,
              marginTop: 24,
              padding: "14px 36px",
              borderRadius: 14,
              border: "1px solid rgba(0, 212, 255, 0.2)",
              background: "rgba(0, 212, 255, 0.04)",
              letterSpacing: 0.5,
            }}
          >
            github.com/steve-cooks/x-brief
          </div>
        </BlurIn>
      </div>
    </AbsoluteFill>
  );
};

// ─── Main Composition ────────────────────────────────────────────────────────

export const XBriefLaunchV2: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg }}>
      <Background />

      {/* Scene 1: The Hook — frames 0–240 */}
      <Sequence from={0} durationInFrames={255}>
        <SceneTheHook />
      </Sequence>

      {/* Scene 2: The Promise — frames 240–480 (15-frame overlap) */}
      <Sequence from={225} durationInFrames={255}>
        <SceneThePromise />
      </Sequence>

      {/* Scene 3: The Hero — frames 480–840 (15-frame overlap) */}
      <Sequence from={465} durationInFrames={375}>
        <SceneTheHero />
      </Sequence>

      {/* Scene 4: Quick Flash — frames 840–960 (15-frame overlap) */}
      <Sequence from={825} durationInFrames={135}>
        <SceneQuickFlash />
      </Sequence>

      {/* Scene 5: The Closer — frames 960–1200 (15-frame overlap) */}
      <Sequence from={945} durationInFrames={255}>
        <SceneTheCloser />
      </Sequence>
    </AbsoluteFill>
  );
};
