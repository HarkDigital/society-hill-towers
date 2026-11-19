// Round 256 (Stage 4, the ASTC art): macOS's own ASTC encoder (ImageIO, org.khronos.astc), so the pipeline needs no
// download. ImageIO writes 4x4 and 8x8 blocks only. bake_astc.py compiles this once (swiftc -O) and feeds it a job file:
// one line a picture, "<in.png>\t<out.astc>\t<44|88>". The input PNGs are written by the bake already flipped and sized;
// ImageIO is told nothing about colour, so the values are encoded as they are (an sRGB map's coded values, a mask's own).
// Prints one line a job: ok or fail and the path.
import Foundation
import ImageIO

let args = CommandLine.arguments
guard args.count == 2, let jobs = try? String(contentsOfFile: args[1], encoding: .utf8) else {
  FileHandle.standardError.write("usage: astc_enc <jobs.tsv>\n".data(using: .utf8)!)
  exit(2)
}
var failed = 0
for line in jobs.split(separator: "\n") {
  let p = line.split(separator: "\t").map(String.init)
  if p.count != 3 { continue }
  let bs = Int(p[2], radix: 16) ?? 0x44
  guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: p[0]) as CFURL, nil),
        let img = CGImageSourceCreateImageAtIndex(src, 0, nil),
        let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: p[1]) as CFURL, "org.khronos.astc" as CFString, 1, nil) else {
    print("fail\t" + p[0]); failed += 1; continue
  }
  CGImageDestinationAddImage(dst, img, ["kCGImagePropertyASTCBlockSize": bs, "kCGImagePropertyEncoder": "kCGImagePropertyASTCEncoder"] as CFDictionary)
  if CGImageDestinationFinalize(dst) { print("ok\t" + p[1]) } else { print("fail\t" + p[0]); failed += 1 }
}
exit(failed == 0 ? 0 : 1)
