import Foundation
import Vision
import CoreImage
import AppKit

// uso: cut in_dir out_dir   (procesa todos los .png de in_dir)
let args = CommandLine.arguments
let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let ctx = CIContext()
let files = try FileManager.default.contentsOfDirectory(at: inDir, includingPropertiesForKeys: nil).filter { $0.pathExtension == "png" }.sorted { $0.lastPathComponent < $1.lastPathComponent }
for f in files {
    let out = outDir.appendingPathComponent(f.lastPathComponent)
    do {
        let handler = VNImageRequestHandler(url: f)
        let req = VNGenerateForegroundInstanceMaskRequest()
        try handler.perform([req])
        guard let obs = req.results?.first else { print("NOMASK", f.lastPathComponent); continue }
        let buf = try obs.generateMaskedImage(ofInstances: obs.allInstances, from: handler, croppedToInstancesExtent: false)
        let ci = CIImage(cvPixelBuffer: buf)
        let cs = CGColorSpace(name: CGColorSpace.sRGB)!
        try ctx.writePNGRepresentation(of: ci, to: out, format: .RGBA8, colorSpace: cs)
        print("OK", f.lastPathComponent)
    } catch { print("ERR", f.lastPathComponent, error) }
}
