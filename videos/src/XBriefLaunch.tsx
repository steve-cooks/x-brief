import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const FONT = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
const X_BLUE = "#1DA1F2";
const CYAN_GREEN = "#14F195";
const PRIMARY = "#FFFFFF";
const SECONDARY = "#8899A6";

const GridOverlay: React.FC = () => (
  <AbsoluteFill
    style={{
      backgroundImage: `
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)
      `,
      backgroundSize: "60px 60px",
    }}
  />
);

const Background: React.FC = () => (
  <AbsoluteFill
    style={{
      background: "linear-gradient(180deg, #000000 0%, #0A0A0A 100%)",
    }}
  />
);

// Scene 1: Problem (0-4s, frames 0-240)
const SceneProblem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const line1Spring = spring({ frame, fps, config: { damping: 20 } });
  const line1Blur = interpolate(line1Spring, [0, 1], [20, 0]);
  const line1Opacity = interpolate(line1Spring, [0, 1], [0, 1]);

  const line2Spring = spring({
    frame: frame - 80,
    fps,
    config: { damping: 20 },
  });
  const line2Blur = interpolate(line2Spring, [0, 1], [20, 0]);
  const line2Opacity = interpolate(line2Spring, [0, 1], [0, 1]);

  // Fade out at end
  const fadeOut = interpolate(frame, [210, 240], [1, 0], {
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
          filter: `blur(${line1Blur}px)`,
          opacity: line1Opacity,
          fontFamily: FONT,
          fontSize: 80,
          fontWeight: 700,
          color: PRIMARY,
          textAlign: "center",
          marginBottom: 30,
        }}
      >
        You scroll X for 2 hours.
      </div>
      <div
        style={{
          filter: `blur(${line2Blur}px)`,
          opacity: line2Opacity,
          fontFamily: FONT,
          fontSize: 80,
          fontWeight: 700,
          color: SECONDARY,
          textAlign: "center",
        }}
      >
        You remember nothing.
      </div>
    </AbsoluteFill>
  );
};

// Scene 2: Solution (4-8s, frames 240-480)
const SceneSolution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: { damping: 18 } });
  const titleScale = interpolate(titleSpring, [0, 1], [0.8, 1]);
  const titleOpacity = interpolate(titleSpring, [0, 1], [0, 1]);

  const taglineSpring = spring({
    frame: frame - 50,
    fps,
    config: { damping: 22 },
  });
  const taglineOpacity = interpolate(taglineSpring, [0, 1], [0, 1]);
  const taglineY = interpolate(taglineSpring, [0, 1], [30, 0]);

  // Glow pulse
  const glowPulse = interpolate(
    Math.sin(frame * 0.05),
    [-1, 1],
    [0.4, 0.8]
  );

  // Fade out
  const fadeOut = interpolate(frame, [210, 240], [1, 0], {
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
          transform: `scale(${titleScale})`,
          opacity: titleOpacity,
          fontFamily: FONT,
          fontSize: 140,
          fontWeight: 800,
          color: PRIMARY,
          textAlign: "center",
          textShadow: `0 0 ${60 * glowPulse}px ${X_BLUE}, 0 0 ${120 * glowPulse}px ${X_BLUE}40`,
          marginBottom: 30,
        }}
      >
        X <span style={{ color: X_BLUE }}>Brief</span>
      </div>
      <div
        style={{
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          fontFamily: FONT,
          fontSize: 42,
          fontWeight: 400,
          color: SECONDARY,
          textAlign: "center",
        }}
      >
        Your entire timeline in one sentence.
      </div>
    </AbsoluteFill>
  );
};

// Scene 3: Features (8-14s, frames 480-840)
const TAB_DATA = [
  { image: "screenshot-tldr.jpg", label: "TL;DR", start: 0 },
  { image: "screenshot-light-foryou.jpg", label: "For You", start: 120 },
  { image: "screenshot.jpg", label: "Following", start: 240 },
];

const SceneFeatures: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {TAB_DATA.map((tab) => {
        const localFrame = frame - tab.start;
        const isActive = localFrame >= 0 && localFrame < 135;

        const enterSpring = spring({
          frame: Math.max(0, localFrame),
          fps,
          config: { damping: 20 },
        });

        const exitOpacity =
          localFrame >= 105
            ? interpolate(localFrame, [105, 135], [1, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            : 1;

        const slideX = interpolate(enterSpring, [0, 1], [80, 0]);
        const opacity = interpolate(enterSpring, [0, 1], [0, 1]) * exitOpacity;

        if (!isActive && localFrame < 0) return null;
        if (opacity <= 0) return null;

        return (
          <AbsoluteFill
            key={tab.label}
            style={{
              justifyContent: "center",
              alignItems: "center",
              opacity,
            }}
          >
            {/* Tab label */}
            <div
              style={{
                fontFamily: FONT,
                fontSize: 36,
                fontWeight: 600,
                color: X_BLUE,
                marginBottom: 24,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}
            >
              {tab.label}
            </div>
            {/* Browser mockup frame */}
            <div
              style={{
                transform: `translateX(${slideX}px)`,
                borderRadius: 16,
                border: `2px solid rgba(255,255,255,0.1)`,
                overflow: "hidden",
                boxShadow: `0 0 60px ${X_BLUE}20, 0 20px 60px rgba(0,0,0,0.6)`,
                width: 700,
                height: 500,
                position: "relative",
                background: "#111",
              }}
            >
              {/* Title bar */}
              <div
                style={{
                  height: 36,
                  background: "rgba(255,255,255,0.05)",
                  display: "flex",
                  alignItems: "center",
                  paddingLeft: 14,
                  gap: 8,
                }}
              >
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: "#FF5F56",
                  }}
                />
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: "#FFBD2E",
                  }}
                />
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: "#27C93F",
                  }}
                />
              </div>
              <Img
                src={staticFile(tab.image)}
                style={{
                  width: "100%",
                  height: "calc(100% - 36px)",
                  objectFit: "cover",
                  objectPosition: "top",
                }}
              />
            </div>
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

// Scene 4: How it works (14-18s, frames 840-1080)
const HOW_LINES = [
  { text: "An AI agent scans your timeline every 4 hours.", delay: 0 },
  { text: "You read one sentence.", delay: 60 },
  { text: "Done.", delay: 120 },
];

const SceneHowItWorks: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeOut = interpolate(frame, [210, 240], [1, 0], {
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
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
        }}
      >
        {HOW_LINES.map((line) => {
          const lineSpring = spring({
            frame: frame - line.delay,
            fps,
            config: { damping: 22 },
          });
          const blur = interpolate(lineSpring, [0, 1], [15, 0]);
          const opacity = interpolate(lineSpring, [0, 1], [0, 1]);
          const y = interpolate(lineSpring, [0, 1], [20, 0]);

          const isLast = line.text === "Done.";

          return (
            <div
              key={line.text}
              style={{
                filter: `blur(${blur}px)`,
                opacity,
                transform: `translateY(${y}px)`,
                fontFamily: FONT,
                fontSize: isLast ? 72 : 52,
                fontWeight: isLast ? 800 : 500,
                color: isLast ? CYAN_GREEN : PRIMARY,
                textAlign: "center",
              }}
            >
              {line.text}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// Scene 5: CTA (18-20s, frames 1080-1200)
const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const line1Spring = spring({ frame, fps, config: { damping: 20 } });
  const line1Opacity = interpolate(line1Spring, [0, 1], [0, 1]);
  const line1Scale = interpolate(line1Spring, [0, 1], [0.9, 1]);

  const line2Spring = spring({
    frame: frame - 40,
    fps,
    config: { damping: 25 },
  });
  const line2Opacity = interpolate(line2Spring, [0, 1], [0, 1]);

  // Subtle pulse on the URL
  const pulse = interpolate(Math.sin(frame * 0.08), [-1, 1], [0.95, 1.05]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          opacity: line1Opacity,
          transform: `scale(${line1Scale})`,
          fontFamily: FONT,
          fontSize: 64,
          fontWeight: 700,
          color: PRIMARY,
          textAlign: "center",
          marginBottom: 40,
        }}
      >
        Open source. Free.
      </div>
      <div
        style={{
          opacity: line2Opacity,
          transform: `scale(${pulse})`,
          fontFamily: FONT,
          fontSize: 40,
          fontWeight: 500,
          color: X_BLUE,
          textAlign: "center",
          textShadow: `0 0 30px ${X_BLUE}60`,
        }}
      >
        github.com/steve-cooks/x-brief
      </div>
    </AbsoluteFill>
  );
};

export const XBriefLaunch: React.FC = () => {
  return (
    <AbsoluteFill>
      <Background />
      <GridOverlay />

      {/* Scene 1: Problem (0-255 with overlap) */}
      <Sequence from={0} durationInFrames={255}>
        <SceneProblem />
      </Sequence>

      {/* Scene 2: Solution (240-495 with overlap) */}
      <Sequence from={240} durationInFrames={255}>
        <SceneSolution />
      </Sequence>

      {/* Scene 3: Features (480-855 with overlap) */}
      <Sequence from={480} durationInFrames={375}>
        <SceneFeatures />
      </Sequence>

      {/* Scene 4: How it works (840-1095 with overlap) */}
      <Sequence from={840} durationInFrames={255}>
        <SceneHowItWorks />
      </Sequence>

      {/* Scene 5: CTA (1080-1200) */}
      <Sequence from={1080} durationInFrames={120}>
        <SceneCTA />
      </Sequence>
    </AbsoluteFill>
  );
};
