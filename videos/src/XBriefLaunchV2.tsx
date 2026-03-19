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
const BACKGROUND = "#0A0A0A";
const SECONDARY = "#8899A6";

const SCREEN_WIDTH = 280;
const SCREEN_HEIGHT = 607;
const PHONE_WIDTH = 308;
const PHONE_HEIGHT = 635;

const clampedInterpolate = (
  value: number,
  input: readonly [number, number],
  output: readonly [number, number]
) =>
  interpolate(value, input, output, {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const getReveal = (
  frame: number,
  fps: number,
  delay = 0,
  config: { damping?: number; stiffness?: number; mass?: number } = {}
) => {
  const progress = spring({
    frame: frame - delay,
    fps,
    config: {
      damping: config.damping ?? 18,
      stiffness: config.stiffness ?? 110,
      mass: config.mass ?? 0.9,
    },
  });

  return {
    progress,
    opacity: clampedInterpolate(progress, [0, 1], [0, 1]),
    blur: clampedInterpolate(progress, [0, 1], [18, 0]),
    translateY: clampedInterpolate(progress, [0, 1], [24, 0]),
    scale: clampedInterpolate(progress, [0, 1], [0.94, 1]),
  };
};

const GridOverlay: React.FC = () => (
  <AbsoluteFill
    style={{
      backgroundImage: `
        linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
      `,
      backgroundSize: "60px 60px",
      opacity: 0.55,
    }}
  />
);

const Background: React.FC = () => (
  <AbsoluteFill
    style={{
      background: BACKGROUND,
      overflow: "hidden",
    }}
  >
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 50% 35%, rgba(29,161,242,0.12) 0%, rgba(29,161,242,0.04) 18%, rgba(10,10,10,0) 48%)",
      }}
    />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0) 25%, rgba(0,0,0,0.18) 100%)",
      }}
    />
  </AbsoluteFill>
);

const SceneContainer: React.FC<{
  children: React.ReactNode;
  opacity?: number;
}> = ({ children, opacity = 1 }) => (
  <AbsoluteFill
    style={{
      justifyContent: "center",
      alignItems: "center",
      opacity,
      padding: "100px 140px",
    }}
  >
    {children}
  </AbsoluteFill>
);

const FadeOutScene: React.FC<{
  start: number;
  end: number;
  children: React.ReactNode;
}> = ({ start, end, children }) => {
  const frame = useCurrentFrame();
  const opacity = clampedInterpolate(frame, [start, end], [1, 0]);

  return <SceneContainer opacity={opacity}>{children}</SceneContainer>;
};

const SceneHook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const reveal = getReveal(frame, fps, 0, { damping: 16, stiffness: 95 });

  return (
    <FadeOutScene start={196} end={240}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 80,
          fontWeight: 700,
          color: "#FFFFFF",
          letterSpacing: "-0.04em",
          textAlign: "center",
          filter: `blur(${reveal.blur}px)`,
          opacity: reveal.opacity,
          transform: `translateY(${reveal.translateY}px) scale(${reveal.scale})`,
          textShadow: "0 12px 48px rgba(0,0,0,0.35)",
        }}
      >
        What if X was read-only?
      </div>
    </FadeOutScene>
  );
};

const PITCH_LINES = [
  { text: "No posting.", delay: 0, fontSize: 60, color: "#FFFFFF", weight: 500 },
  { text: "No liking.", delay: 40, fontSize: 60, color: "#FFFFFF", weight: 500 },
  { text: "No scrolling.", delay: 80, fontSize: 60, color: "#FFFFFF", weight: 500 },
  {
    text: "Just the signal.",
    delay: 140,
    fontSize: 72,
    color: X_BLUE,
    weight: 800,
  },
] as const;

const ScenePitch: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fadeOut = clampedInterpolate(frame, [200, 240], [1, 0]);

  return (
    <SceneContainer opacity={fadeOut}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
        {PITCH_LINES.map((line) => {
          const reveal = getReveal(frame, fps, line.delay, {
            damping: 17,
            stiffness: 105,
          });
          const glow =
            line.text === "Just the signal."
              ? clampedInterpolate(Math.sin((frame - line.delay) * 0.08), [-1, 1], [0.45, 1])
              : 0;

          return (
            <div
              key={line.text}
              style={{
                fontFamily: FONT,
                fontSize: line.fontSize,
                fontWeight: line.weight,
                color: line.color,
                letterSpacing: line.text === "Just the signal." ? "-0.05em" : "-0.03em",
                filter: `blur(${reveal.blur}px)`,
                opacity: reveal.opacity,
                transform: `translateY(${reveal.translateY}px) scale(${reveal.scale})`,
                textShadow:
                  line.text === "Just the signal."
                    ? `0 0 ${24 * glow}px rgba(29,161,242,0.85), 0 0 ${64 * glow}px rgba(29,161,242,0.28)`
                    : "0 10px 32px rgba(0,0,0,0.28)",
              }}
            >
              {line.text}
            </div>
          );
        })}
      </div>
    </SceneContainer>
  );
};

const PRODUCT_TABS = [
  { src: staticFile("tldr-tab.png"), label: "TL;DR", start: 0, end: 150 },
  { src: staticFile("foryou-tab.png"), label: "For You", start: 150, end: 300 },
  { src: staticFile("following-tab.png"), label: "Following", start: 300, end: 480 },
] as const;

const PhoneMockup: React.FC<{
  src: string;
  opacity: number;
}> = ({ src, opacity }) => (
  <div
    style={{
      width: PHONE_WIDTH,
      height: PHONE_HEIGHT,
      borderRadius: 44,
      position: "relative",
      background:
        "linear-gradient(180deg, rgba(38,38,38,0.96) 0%, rgba(12,12,12,0.98) 100%)",
      border: "1px solid rgba(255,255,255,0.15)",
      boxShadow:
        "0 20px 80px rgba(29,161,242,0.15), 0 30px 60px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.1)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      opacity,
    }}
  >
    <div
      style={{
        width: SCREEN_WIDTH,
        height: SCREEN_HEIGHT,
        borderRadius: 38,
        overflow: "hidden",
        position: "relative",
        background: "#FFFFFF",
        boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.05)",
      }}
    >
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: "center top",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 14,
          left: "50%",
          transform: "translateX(-50%)",
          width: 126,
          height: 34,
          borderRadius: 999,
          background:
            "linear-gradient(180deg, rgba(0,0,0,1) 0%, rgba(12,12,12,0.98) 100%)",
          boxShadow: "0 2px 10px rgba(0,0,0,0.35)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: 38,
          boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.04)",
          pointerEvents: "none",
        }}
      />
    </div>
    <div
      style={{
        position: "absolute",
        inset: 0,
        borderRadius: 44,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.12)",
        pointerEvents: "none",
      }}
    />
  </div>
);

const SceneProductShowcase: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrance = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 90, mass: 0.95 },
  });
  const scale = clampedInterpolate(entrance, [0, 1], [0.85, 1]);
  const entranceOpacity = clampedInterpolate(entrance, [0, 1], [0, 1]);
  const exitOpacity = clampedInterpolate(frame, [432, 480], [1, 0]);
  const containerOpacity = entranceOpacity * exitOpacity;

  return (
    <SceneContainer opacity={containerOpacity}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
          transform: `scale(${scale})`,
        }}
      >
        <div
          style={{
            position: "relative",
            minHeight: 44,
            width: 320,
            fontFamily: FONT,
            fontSize: 32,
            fontWeight: 700,
            letterSpacing: "0.1em",
            color: X_BLUE,
            textTransform: "uppercase",
            textShadow: "0 0 22px rgba(29,161,242,0.35)",
          }}
        >
          {PRODUCT_TABS.map((tab) => {
            const tabOpacity = clampedInterpolate(frame, [tab.start, tab.start + 20], [0, 1]);
            const tabExit = clampedInterpolate(frame, [tab.end - 20, tab.end], [1, 0]);
            const opacity = tabOpacity * tabExit;

            if (opacity <= 0) {
              return null;
            }

            return (
              <div
                key={tab.label}
                style={{
                  position: "absolute",
                  left: "50%",
                  transform: `translateX(-50%) translateY(${clampedInterpolate(
                    opacity,
                    [0, 1],
                    [8, 0]
                  )}px)`,
                  opacity,
                }}
              >
                {tab.label}
              </div>
            );
          })}
        </div>
        <div
          style={{
            position: "relative",
            width: PHONE_WIDTH,
            height: PHONE_HEIGHT,
          }}
        >
          {PRODUCT_TABS.map((tab) => {
            const enterOpacity = clampedInterpolate(frame, [tab.start, tab.start + 20], [0, 1]);
            const leaveOpacity = clampedInterpolate(frame, [tab.end - 18, tab.end], [1, 0]);
            const opacity = enterOpacity * leaveOpacity;

            if (opacity <= 0) {
              return null;
            }

            return (
              <div
                key={tab.label}
                style={{
                  position: "absolute",
                  inset: 0,
                }}
              >
                <PhoneMockup src={tab.src} opacity={opacity} />
              </div>
            );
          })}
        </div>
      </div>
    </SceneContainer>
  );
};

const SceneTagline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const reveal = getReveal(frame, fps, 0, { damping: 15, stiffness: 90 });
  const glowPulse = clampedInterpolate(Math.sin(frame * 0.09), [-1, 1], [0.5, 1]);

  return (
    <SceneContainer>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
          transform: `translateY(${reveal.translateY}px) scale(${clampedInterpolate(
            reveal.progress,
            [0, 1],
            [0.9, 1]
          )})`,
          opacity: reveal.opacity,
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 120,
            fontWeight: 800,
            letterSpacing: "-0.06em",
            color: "#FFFFFF",
            textShadow: `0 0 ${28 * glowPulse}px rgba(29,161,242,0.18)`,
          }}
        >
          X <span style={{ color: X_BLUE }}>Brief</span>
        </div>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 44,
            fontWeight: 400,
            color: SECONDARY,
            letterSpacing: "-0.03em",
          }}
        >
          your read-only X account
        </div>
      </div>
    </SceneContainer>
  );
};

const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const reveal = getReveal(frame, fps, 0, { damping: 16, stiffness: 92 });
  const urlReveal = getReveal(frame, fps, 16, { damping: 18, stiffness: 105 });
  const pulse = clampedInterpolate(Math.sin((frame - 10) * 0.12), [-1, 1], [0.985, 1.025]);

  return (
    <SceneContainer>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 18,
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 56,
            fontWeight: 600,
            color: "#FFFFFF",
            letterSpacing: "-0.04em",
            opacity: reveal.opacity,
            transform: `translateY(${reveal.translateY}px) scale(${reveal.scale})`,
          }}
        >
          Try it free
        </div>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 42,
            fontWeight: 700,
            color: X_BLUE,
            letterSpacing: "-0.03em",
            opacity: urlReveal.opacity,
            transform: `translateY(${urlReveal.translateY}px) scale(${pulse})`,
            textShadow: "0 0 24px rgba(29,161,242,0.65), 0 0 48px rgba(29,161,242,0.18)",
          }}
        >
          xbrief.app
        </div>
      </div>
    </SceneContainer>
  );
};

export const XBriefLaunchV2: React.FC = () => {
  return (
    <AbsoluteFill>
      <Background />
      <GridOverlay />

      <Sequence from={0} durationInFrames={240}>
        <SceneHook />
      </Sequence>

      <Sequence from={240} durationInFrames={240}>
        <ScenePitch />
      </Sequence>

      <Sequence from={480} durationInFrames={480}>
        <SceneProductShowcase />
      </Sequence>

      <Sequence from={960} durationInFrames={150}>
        <SceneTagline />
      </Sequence>

      <Sequence from={1110} durationInFrames={90}>
        <SceneCTA />
      </Sequence>
    </AbsoluteFill>
  );
};
