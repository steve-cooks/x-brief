import React from "react";
import { Composition } from "remotion";
import { XBriefLaunch } from "./XBriefLaunch";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="XBrief-Launch"
      component={XBriefLaunch}
      durationInFrames={1200}
      fps={60}
      width={1920}
      height={1080}
    />
  );
};
