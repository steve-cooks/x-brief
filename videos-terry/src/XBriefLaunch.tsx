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
  bg: "#0A0A0A",
  bgDeep: "#050505",
  accent: "#1DA1F2",
  amber: "#F5A623",
  text: "#FFFFFF",
  textSecondary: "#A0A0A0",
  textMuted: "#555555",
  grid: "rgba(51,51,51,0.12)",
};

const FONTS = {
  heading:
    "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif",
  mono: "'JetBrains Mono', 'SF Mono', monospace",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

const BlurIn: React.FC<{
  children: React.ReactNode;
  delay?: number;
  durationInFrames?: number;
}> = ({ children, delay = 0, durationInFrames = 45 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({
    fps,
    frame,
    config: { damping: 200 },
    delay,
    durationInFrames,
  });
  const blur = interpolate(progress, [0, 1], [20, 0]);
  const translateY = interpolate(progress, [0, 1], [30, 0]);
  const opacity = interpolate(progress, [0, 0.5, 1], [0, 0.8, 1]);
  return (
    <div
      style={{
        filter: `blur(${blur}px)`,
        transform: `translateY(${translateY}px)`,
        opacity,
      }}
    >
      {children}
    </div>
  );
};

const Background: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Gradient background */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, ${COLORS.bg} 0%, ${COLORS.bgDeep} 100%)`,
        }}
      />
      {/* Grid */}
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${COLORS.grid} 1px, transparent 1px), linear-gradient(90deg, ${COLORS.grid} 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
        }}
      />
      {/* Noise overlay */}
      <AbsoluteFill
        style={{
          opacity: 0.03,
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
          backgroundSize: "256px 256px",
        }}
      />
      {/* Vignette */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.6) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

// ─── Scene 1: The Pain (frames 0-240) ────────────────────────────────────────

const SceneThePain: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Scroll counter: 0 → 120 minutes over ~180 frames, holds at 120
  const counterProgress = Math.min(frame / 180, 1);
  const eased = 1 - Math.pow(1 - counterProgress, 3); // ease-out cubic
  const minutes = Math.round(eased * 120);

  let timeDisplay: string;
  if (minutes < 60) {
    timeDisplay = `${minutes} minutes`;
  } else {
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (mins === 0) {
      timeDisplay = `${hrs} hour${hrs > 1 ? "s" : ""}`;
    } else {
      timeDisplay = `${hrs}h ${mins}m`;
    }
  }

  // Blue glow pulse
  const glowOpacity = interpolate(
    Math.sin(frame * 0.05),
    [-1, 1],
    [0.05, 0.15]
  );

  // Fade out at end (frames 220-240 of this sequence)
  const fadeOut = interpolate(frame, [220, 240], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const blurOut = interpolate(frame, [220, 240], [0, 12], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOut,
        filter: `blur(${blurOut}px)`,
      }}
    >
      {/* Subtle blue glow */}
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: COLORS.accent,
          filter: "blur(200px)",
          opacity: glowOpacity,
        }}
      />

      {/* Counter */}
      <BlurIn delay={10} durationInFrames={40}>
        <div
          style={{
            fontFamily: FONTS.mono,
            fontSize: 96,
            fontWeight: 700,
            color: COLORS.text,
            letterSpacing: "-2px",
            textAlign: "center",
          }}
        >
          {timeDisplay}
        </div>
      </BlurIn>

      {/* Subtitle */}
      <BlurIn delay={30} durationInFrames={50}>
        <div
          style={{
            fontFamily: FONTS.heading,
            fontSize: 36,
            color: COLORS.textSecondary,
            marginTop: 24,
            textAlign: "center",
          }}
        >
          You spent <span style={{ color: COLORS.text }}>2 hours</span>{" "}
          scrolling X today
        </div>
      </BlurIn>
    </AbsoluteFill>
  );
};

// ─── Scene 2: The Reveal (frames 240-420) ────────────────────────────────────

const SceneTheReveal: React.FC = () => {
  const frame = useCurrentFrame();

  // Fade out at end
  const fadeOut = interpolate(frame, [160, 180], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const blurOut = interpolate(frame, [160, 180], [0, 10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOut,
        filter: `blur(${blurOut}px)`,
      }}
    >
      <BlurIn delay={15} durationInFrames={50}>
        <div
          style={{
            fontFamily: FONTS.heading,
            fontSize: 56,
            fontWeight: 600,
            color: COLORS.text,
            textAlign: "center",
            lineHeight: 1.4,
            maxWidth: 900,
          }}
        >
          What if you could get caught up
          <br />
          in{" "}
          <span style={{ color: COLORS.accent, fontWeight: 700 }}>
            5 minutes
          </span>
          ?
        </div>
      </BlurIn>
    </AbsoluteFill>
  );
};

// ─── Scene 3: Product Showcase (frames 420-750) ──────────────────────────────

const TABS = [
  {
    image: "screenshot-tldr.jpg",
    label: "TL;DR",
    description: "One sentence. You're caught up.",
  },
  {
    image: "screenshot-light-foryou.jpg",
    label: "For You",
    description: "Posts matched to your interests",
  },
  {
    image: "screenshot.jpg",
    label: "Following",
    description: "From accounts you actually care about",
  },
];

const PhoneMockup: React.FC<{
  imageSrc: string;
  opacity: number;
  scale: number;
  blur: number;
}> = ({ imageSrc, opacity, scale, blur }) => {
  return (
    <div
      style={{
        position: "absolute",
        opacity,
        transform: `scale(${scale})`,
        filter: `blur(${blur}px)`,
      }}
    >
      {/* Phone frame */}
      <div
        style={{
          width: 320,
          height: 640,
          borderRadius: 36,
          border: "3px solid rgba(255,255,255,0.15)",
          overflow: "hidden",
          background: "#000",
          boxShadow: `0 0 80px rgba(29,161,242,0.15), 0 20px 60px rgba(0,0,0,0.5)`,
        }}
      >
        {/* Status bar area */}
        <div style={{ height: 44, background: "#000" }} />
        <Img
          src={staticFile(imageSrc)}
          style={{
            width: 320,
            height: 596,
            objectFit: "cover",
            objectPosition: "top",
          }}
        />
      </div>
    </div>
  );
};

const SceneProductShowcase: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Each tab gets ~100 frames of visibility, with crossfade
  const tabDuration = 100;
  const activeTabIndex = Math.min(
    Math.floor(frame / tabDuration),
    TABS.length - 1
  );

  // Phone entrance animation
  const phoneEntrance = spring({
    fps,
    frame,
    config: { damping: 20 },
    delay: 0,
    durationInFrames: 40,
  });
  const phoneScale = interpolate(phoneEntrance, [0, 1], [0.9, 1]);
  const phoneOpacity = interpolate(phoneEntrance, [0, 1], [0, 1]);

  // Fade out at end
  const fadeOut = interpolate(frame, [310, 330], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOut,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 80,
        }}
      >
        {/* Phone */}
        <div style={{ position: "relative", width: 320, height: 640 }}>
          {TABS.map((tab, i) => {
            const tabStart = i * tabDuration;
            const tabOpacity = interpolate(
              frame,
              [
                tabStart,
                tabStart + 20,
                tabStart + tabDuration - 20,
                tabStart + tabDuration,
              ],
              [0, 1, 1, i === TABS.length - 1 ? 1 : 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return (
              <PhoneMockup
                key={tab.label}
                imageSrc={tab.image}
                opacity={tabOpacity * phoneOpacity}
                scale={phoneScale}
                blur={0}
              />
            );
          })}
        </div>

        {/* Labels */}
        <div style={{ width: 500 }}>
          {TABS.map((tab, i) => {
            const tabStart = i * tabDuration;
            const labelProgress = spring({
              fps,
              frame: Math.max(0, frame - tabStart),
              config: { damping: 18 },
              durationInFrames: 35,
            });
            const labelOpacity = interpolate(
              frame,
              [
                tabStart,
                tabStart + 15,
                tabStart + tabDuration - 20,
                tabStart + tabDuration,
              ],
              [0, 1, 1, i === TABS.length - 1 ? 1 : 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const labelBlur = interpolate(labelProgress, [0, 1], [15, 0]);
            const labelTranslate = interpolate(
              labelProgress,
              [0, 1],
              [20, 0]
            );

            return (
              <div
                key={tab.label}
                style={{
                  position: "absolute",
                  right: 160,
                  top: "50%",
                  transform: `translateY(-50%) translateY(${labelTranslate}px)`,
                  opacity: labelOpacity,
                  filter: `blur(${labelBlur}px)`,
                  width: 500,
                }}
              >
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 22,
                    color: COLORS.accent,
                    marginBottom: 12,
                    letterSpacing: "2px",
                    textTransform: "uppercase",
                  }}
                >
                  {tab.label}
                </div>
                <div
                  style={{
                    fontFamily: FONTS.heading,
                    fontSize: 40,
                    fontWeight: 600,
                    color: COLORS.text,
                    lineHeight: 1.3,
                  }}
                >
                  {tab.description}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Scene 4: How It Works (frames 750-960) ──────────────────────────────────

const STEPS = [
  { icon: "\uD83E\uDD16", text: "Agent scans X every 4 hours" },
  { icon: "\uD83E\uDDE0", text: "AI curates what matters to you" },
  { icon: "\uD83D\uDCF1", text: "5-minute brief, ready when you are" },
];

const SceneHowItWorks: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade out at end
  const fadeOut = interpolate(frame, [190, 210], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOut,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 48 }}>
        {STEPS.map((step, i) => {
          const stepDelay = 10 + i * 35;
          const progress = spring({
            fps,
            frame,
            config: { damping: 20 },
            delay: stepDelay,
            durationInFrames: 40,
          });
          const blur = interpolate(progress, [0, 1], [20, 0]);
          const translateX = interpolate(progress, [0, 1], [40, 0]);
          const opacity = interpolate(
            progress,
            [0, 0.5, 1],
            [0, 0.8, 1]
          );

          return (
            <div
              key={step.text}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 28,
                opacity,
                filter: `blur(${blur}px)`,
                transform: `translateX(${translateX}px)`,
              }}
            >
              <div style={{ fontSize: 48 }}>{step.icon}</div>
              <div
                style={{
                  fontFamily: FONTS.heading,
                  fontSize: 36,
                  fontWeight: 500,
                  color: COLORS.text,
                }}
              >
                {step.text}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ─── Scene 5: CTA / Outro (frames 960-1200) ──────────────────────────────────

const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Subtle pulse on GitHub link
  const pulse = interpolate(Math.sin(frame * 0.08), [-1, 1], [0.85, 1]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* Accent glow behind title */}
      <div
        style={{
          position: "absolute",
          width: 400,
          height: 400,
          borderRadius: "50%",
          background: COLORS.accent,
          filter: "blur(180px)",
          opacity: 0.08,
          top: "30%",
        }}
      />

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
        {/* Title */}
        <BlurIn delay={5} durationInFrames={40}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 96,
              fontWeight: 800,
              color: COLORS.text,
              letterSpacing: "-3px",
            }}
          >
            X Brief
          </div>
        </BlurIn>

        {/* Tagline */}
        <BlurIn delay={20} durationInFrames={45}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 30,
              fontWeight: 400,
              color: COLORS.textSecondary,
              textAlign: "center",
              maxWidth: 750,
              lineHeight: 1.5,
            }}
          >
            Replace{" "}
            <span style={{ color: COLORS.amber }}>2 hours of scrolling</span>{" "}
            with{" "}
            <span style={{ color: COLORS.accent }}>5 minutes of signal</span>
          </div>
        </BlurIn>

        {/* Badges */}
        <BlurIn delay={40} durationInFrames={45}>
          <div
            style={{
              fontFamily: FONTS.heading,
              fontSize: 20,
              color: COLORS.textMuted,
              marginTop: 8,
              letterSpacing: "3px",
              textTransform: "uppercase",
            }}
          >
            Open Source &middot; Free &middot; Built with OpenClaw
          </div>
        </BlurIn>

        {/* GitHub link */}
        <BlurIn delay={55} durationInFrames={45}>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 26,
              color: COLORS.accent,
              marginTop: 20,
              opacity: pulse,
              transform: `scale(${pulse})`,
              padding: "12px 32px",
              borderRadius: 12,
              border: `1px solid rgba(29,161,242,0.25)`,
              background: "rgba(29,161,242,0.05)",
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

export const XBriefLaunch: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgDeep }}>
      <Background />

      {/* Scene 1: The Pain — 0-240 */}
      <Sequence from={0} durationInFrames={255}>
        <SceneThePain />
      </Sequence>

      {/* Scene 2: The Reveal — 240-420 (overlaps scene 1 by 15 frames) */}
      <Sequence from={225} durationInFrames={195}>
        <SceneTheReveal />
      </Sequence>

      {/* Scene 3: Product Showcase — 420-750 (overlaps scene 2 by 15 frames) */}
      <Sequence from={405} durationInFrames={345}>
        <SceneProductShowcase />
      </Sequence>

      {/* Scene 4: How It Works — 750-960 (overlaps scene 3 by 15 frames) */}
      <Sequence from={735} durationInFrames={225}>
        <SceneHowItWorks />
      </Sequence>

      {/* Scene 5: CTA / Outro — 960-1200 (overlaps scene 4 by 15 frames) */}
      <Sequence from={945} durationInFrames={255}>
        <SceneCTA />
      </Sequence>
    </AbsoluteFill>
  );
};
