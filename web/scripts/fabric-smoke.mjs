import { Canvas, FabricImage, IText } from 'fabric/node'

const canvas = new Canvas(undefined, {
  width: 320,
  height: 240,
  backgroundColor: '#ffffff',
})

const text = new IText('Fabric 7 smoke', {
  left: 160,
  top: 60,
  originX: 'center',
  originY: 'center',
  fontSize: 24,
  fill: '#111827',
})
canvas.add(text)
canvas.bringObjectToFront(text)

const image = await FabricImage.fromURL(
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="80" height="80"%3E%3Crect width="80" height="80" fill="%23f59e0b"/%3E%3C/svg%3E'
)
image.set({
  left: 160,
  top: 150,
  originX: 'center',
  originY: 'center',
})
canvas.add(image)

const json = canvas.toJSON()
const clone = new Canvas(undefined, { width: 320, height: 240 })
await clone.loadFromJSON(json)

const dataUrl = clone.toDataURL({ format: 'png', multiplier: 1 })
if (!dataUrl.startsWith('data:image/png;base64,')) {
  throw new Error('Fabric PNG export failed')
}

console.log(`fabric ${json.version}; objects=${clone.getObjects().length}; dataUrl=${dataUrl.length}`)

canvas.dispose()
clone.dispose()
