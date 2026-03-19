import React from "react";
import { Composition } from "remotion";
import { XBriefLaunch } from "./XBriefLaunch";
import { XBriefLaunchV2 } from "./XBriefLaunchV2";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="XBrief-Launch"
        component={XBriefLaunch}
        durationInFrames={1200}
        fps={60}
        width={1920}
        height={1080}
      />
      <Composition
        id="XBrief-Launch-V2"
        component={XBriefLaunchV2}
        durationInFrames={1200}
        fps={60}
        width={1920}
        height={1080}
      />
    </>
  );
};
