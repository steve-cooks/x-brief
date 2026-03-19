import { Composition } from "remotion";
import { XBriefLaunch } from "./XBriefLaunch";
import { XBriefLaunchV2 } from "./XBriefLaunchV2";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="XBriefLaunch"
        component={XBriefLaunch}
        durationInFrames={1200}
        fps={60}
        width={1920}
        height={1080}
      />
      <Composition
        id="XBriefLaunchV2"
        component={XBriefLaunchV2}
        durationInFrames={1200}
        fps={60}
        width={1920}
        height={1080}
      />
    </>
  );
};
