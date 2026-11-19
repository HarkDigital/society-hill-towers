// Round 262: every frame (or n a second) of a video as JPEGs, with AVFoundation (this Mac has no ffmpeg), the track's
// rotation applied (an iPhone screen recording comes out upright), at most 1100 pixels on a side.
// usage: swift video_frames.swift <video> <out dir> <frames a second>   (names: f####_<seconds>.jpg)
import AVFoundation
import AppKit
let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1]); let out = args[2]; let fps = Double(args[3])!
let asset = AVURLAsset(url: url)
let dur = CMTimeGetSeconds(asset.duration)
let tr = asset.tracks(withMediaType: .video).first!
print("duration", dur, "size", tr.naturalSize, "fps", tr.nominalFrameRate, "transform", tr.preferredTransform)
let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = .zero; gen.requestedTimeToleranceAfter = .zero
gen.maximumSize = CGSize(width: 1100, height: 1100)
var t = 0.0; var i = 0
while t < dur {
  let cg = try! gen.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil)
  let rep = NSBitmapImageRep(cgImage: cg)
  let d = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.8])!
  try! d.write(to: URL(fileURLWithPath: String(format: "%@/f%04d_%06.2f.jpg", out, i, t)))
  t += 1.0/fps; i += 1
}
print("frames", i)
