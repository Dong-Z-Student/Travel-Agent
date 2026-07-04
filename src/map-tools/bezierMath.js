const getBezierPoint = (points, t) => {
  if (points.length === 1) return points[0]

  const nextPoints = []
  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index]
    const end = points[index + 1]
    nextPoints.push([
      start[0] * (1 - t) + end[0] * t,
      start[1] * (1 - t) + end[1] * t
    ])
  }

  return getBezierPoint(nextPoints, t)
}

export const sampleBezierCurve = (controlPoints, sampleCount = 64) => {
  if (controlPoints.length < 3) return controlPoints

  const samples = []
  for (let index = 0; index <= sampleCount; index += 1) {
    const t = Math.round((index / sampleCount) * 1000) / 1000
    samples.push(getBezierPoint(controlPoints, t))
  }

  return samples
}
