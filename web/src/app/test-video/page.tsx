export default function TestVideo() {
  const videoUrl = `/api/media?url=${encodeURIComponent("https://video.twimg.com/amplify_video/2020950780396830723/vid/avc1/720x596/7YzZ51EmAOXP4QbO.mp4")}`
  const posterUrl = `/api/media?url=${encodeURIComponent("https://pbs.twimg.com/amplify_video_thumb/2020950780396830723/img/vjBp0UrEi5YhQsqm.jpg")}`
  const gifUrl = `/api/media?url=${encodeURIComponent("https://video.twimg.com/tweet_video/HAx8DykaAAARcgE.mp4")}`
  
  return (
    <div style={{ padding: 20, maxWidth: 600 }}>
      <h2>Video Test (proxied)</h2>
      <video src={videoUrl} poster={posterUrl} controls autoPlay muted playsInline style={{ width: "100%", borderRadius: 12 }} />
      <h2>GIF Test (proxied)</h2>
      <video src={gifUrl} autoPlay loop muted playsInline style={{ width: "100%", borderRadius: 12 }} />
    </div>
  )
}
