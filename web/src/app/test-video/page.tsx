export default function TestVideo() {
  return (
    <div style={{ padding: 20 }}>
      <h2>Video Test (with referrerPolicy no-referrer)</h2>
      <video 
        src="https://video.twimg.com/amplify_video/2020950780396830723/vid/avc1/720x596/7YzZ51EmAOXP4QbO.mp4" 
        poster="https://pbs.twimg.com/amplify_video_thumb/2020950780396830723/img/vjBp0UrEi5YhQsqm.jpg"
        controls 
        autoPlay 
        muted 
        playsInline
        // @ts-expect-error referrerPolicy valid on video
        referrerPolicy="no-referrer"
        crossOrigin="anonymous"
        style={{ maxWidth: 600, borderRadius: 12 }}
      />
      <h2>GIF Test (with referrerPolicy no-referrer)</h2>
      <video 
        src="https://video.twimg.com/tweet_video/HAx8DykaAAARcgE.mp4"
        poster="https://pbs.twimg.com/tweet_video_thumb/HAx8DykaAAARcgE.jpg"
        autoPlay 
        loop 
        muted 
        playsInline
        // @ts-expect-error referrerPolicy valid on video  
        referrerPolicy="no-referrer"
        crossOrigin="anonymous"
        style={{ maxWidth: 600, borderRadius: 12 }}
      />
    </div>
  )
}
