// Apple Vision subject lift: eyetoo-lift <input> <output.png>
import CoreImage
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count == 3 else { fputs("usage: eyetoo-lift <input> <output.png>\n", stderr); exit(2) }
let handler = VNImageRequestHandler(url: URL(fileURLWithPath: args[1]))
let request = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([request])
guard let result = request.results?.first else { fputs("eyetoo-lift: no subject found in \(args[1])\n", stderr); exit(1) }
let masked = try result.generateMaskedImage(ofInstances: result.allInstances, from: handler, croppedToInstancesExtent: false)
try CIContext().writePNGRepresentation(
    of: CIImage(cvPixelBuffer: masked), to: URL(fileURLWithPath: args[2]),
    format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
