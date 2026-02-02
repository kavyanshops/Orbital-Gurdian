"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"
import * as satellite from "satellite.js"

interface SatelliteData {
    name: string
    line1: string
    line2: string
    type?: 'satellite' | 'featured' | 'background' | 'debris'
}

interface RotatingEarthProps {
    width?: number
    height?: number
    className?: string
    satellites?: SatelliteData[]
}

export default function RotatingEarth({ width = 800, height = 600, className = "", satellites = [] }: RotatingEarthProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const mousePos = useRef<[number, number] | null>(null)

    // Cache satrecs to avoid re-parsing every frame
    const satrecsRef = useRef<any[]>([])

    // Parse TLEs whenever the prop changes
    useEffect(() => {
        if (satellites.length > 0) {
            satrecsRef.current = satellites.map(sat => ({
                ...sat,
                satrec: satellite.twoline2satrec(sat.line1, sat.line2)
            }))
        }
    }, [satellites])

    // Use isLoading to suppress unused warning (or render loading state)
    useEffect(() => {
        if (!isLoading) {
            // console.log("Globe loaded")
        }
    }, [isLoading])

    useEffect(() => {
        if (!canvasRef.current) return

        const canvas = canvasRef.current
        const context = canvas.getContext("2d")
        if (!context) return

        // Set up responsive dimensions
        const containerWidth = Math.min(width, window.innerWidth - 40)
        const containerHeight = Math.min(height, window.innerHeight - 100)
        const radius = Math.min(containerWidth, containerHeight) / 2.5

        const dpr = window.devicePixelRatio || 1
        canvas.width = containerWidth * dpr
        canvas.height = containerHeight * dpr
        canvas.style.width = `${containerWidth}px`
        canvas.style.height = `${containerHeight}px`
        context.scale(dpr, dpr)

        // Create projection and path generator for Canvas
        const projection = d3
            .geoOrthographic()
            .scale(radius)
            .translate([containerWidth / 2, containerHeight / 2])
            .clipAngle(90)

        const path = d3.geoPath().projection(projection).context(context)

        const pointInPolygon = (point: [number, number], polygon: number[][]): boolean => {
            const [x, y] = point
            let inside = false

            for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
                const [xi, yi] = polygon[i]
                const [xj, yj] = polygon[j]

                if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
                    inside = !inside
                }
            }

            return inside
        }

        const pointInFeature = (point: [number, number], feature: any): boolean => {
            const geometry = feature.geometry

            if (geometry.type === "Polygon") {
                const coordinates = geometry.coordinates
                // Check if point is in outer ring
                if (!pointInPolygon(point, coordinates[0])) {
                    return false
                }
                // Check if point is in any hole (inner rings)
                for (let i = 1; i < coordinates.length; i++) {
                    if (pointInPolygon(point, coordinates[i])) {
                        return false // Point is in a hole
                    }
                }
                return true
            } else if (geometry.type === "MultiPolygon") {
                // Check each polygon in the MultiPolygon
                for (const polygon of geometry.coordinates) {
                    // Check if point is in outer ring
                    if (pointInPolygon(point, polygon[0])) {
                        // Check if point is in any hole
                        let inHole = false
                        for (let i = 1; i < polygon.length; i++) {
                            if (pointInPolygon(point, polygon[i])) {
                                inHole = true
                                break
                            }
                        }
                        if (!inHole) {
                            return true
                        }
                    }
                }
                return false
            }

            return false
        }

        const generateDotsInPolygon = (feature: any, dotSpacing = 16) => {
            const dots: [number, number][] = []
            const bounds = d3.geoBounds(feature)
            const [[minLng, minLat], [maxLng, maxLat]] = bounds

            const stepSize = dotSpacing * 0.08
            let pointsGenerated = 0

            for (let lng = minLng; lng <= maxLng; lng += stepSize) {
                for (let lat = minLat; lat <= maxLat; lat += stepSize) {
                    const point: [number, number] = [lng, lat]
                    if (pointInFeature(point, feature)) {
                        dots.push(point)
                        pointsGenerated++
                    }
                }
            }
            return dots
        }

        interface DotData {
            lng: number
            lat: number
            visible: boolean
        }

        const allDots: DotData[] = []
        let landFeatures: any

        // Helper to generate orbit path
        const getOrbitPath = (satrec: any, time: Date) => {
            const pathCoords: [number, number][] = []
            // Propagate for one full orbit (~90-100 mins)
            // Step size: 1 minute
            for (let i = 0; i < 100; i++) {
                const t = new Date(time.getTime() + i * 60000)
                const pv = satellite.propagate(satrec, t)
                if (pv && pv.position) {
                    const pos = pv.position
                    if (pos && typeof pos !== 'boolean') {
                        const gmst = satellite.gstime(t)
                        const geo = satellite.eciToGeodetic(pos, gmst)
                        const lng = satellite.degreesLong(geo.longitude)
                        const lat = satellite.degreesLat(geo.latitude)
                        pathCoords.push([lng, lat])
                    }
                }
            }
            return pathCoords
        }

        const render = () => {
            // Clear canvas
            context.clearRect(0, 0, containerWidth, containerHeight)

            const currentScale = projection.scale()
            const scaleFactor = currentScale / radius

            // Draw ocean (globe background)
            context.beginPath()
            context.arc(containerWidth / 2, containerHeight / 2, currentScale, 0, 2 * Math.PI)
            context.fillStyle = "#02040a" // Very dark blue/black
            context.fill()
            context.strokeStyle = "#1e293b" // Slate 800
            context.lineWidth = 1 * scaleFactor
            context.stroke()

            if (landFeatures) {
                // Draw graticule
                const graticule = d3.geoGraticule()
                context.beginPath()
                path(graticule())
                context.strokeStyle = "#334155" // Slate 700
                context.lineWidth = 0.5 * scaleFactor
                context.globalAlpha = 0.2
                context.stroke()
                context.globalAlpha = 1

                // Draw land outlines
                context.beginPath()
                landFeatures.features.forEach((feature: any) => {
                    path(feature)
                })
                context.strokeStyle = "#475569" // Slate 600
                context.lineWidth = 0.8 * scaleFactor
                context.globalAlpha = 0.3
                context.stroke()
                context.globalAlpha = 1

                // Draw halftone dots
                allDots.forEach((dot) => {
                    const projected = projection([dot.lng, dot.lat])
                    if (projected) {
                        context.beginPath()
                        context.arc(projected[0], projected[1], 1.0 * scaleFactor, 0, 2 * Math.PI)
                        context.fillStyle = "#94a3b8" // Slate 400
                        context.fill()
                    }
                })
            }

            // --- DRAW SATELLITES ---
            let hoveredSat: any = null
            let minDist = 20 // Hit threshold in pixels

            if (satrecsRef.current.length > 0) {
                const now = new Date()

                satrecsRef.current.forEach(sat => {
                    const positionAndVelocity = satellite.propagate(sat.satrec, now)
                    if (!positionAndVelocity || !positionAndVelocity.position) return;

                    const positionEci = positionAndVelocity.position

                    if (positionEci && typeof positionEci !== 'boolean') {
                        // ECI -> Geodetic
                        const gmst = satellite.gstime(now)
                        const geodetic = satellite.eciToGeodetic(positionEci, gmst)

                        // Geodetic (Radians) -> Geodetic (Degrees)
                        const longitude = satellite.degreesLong(geodetic.longitude)
                        const latitude = satellite.degreesLat(geodetic.latitude)

                        // Project
                        const projected = projection([longitude, latitude])

                        if (projected) {
                            // Check Hover
                            if (mousePos.current) {
                                const dx = projected[0] - mousePos.current[0]
                                const dy = projected[1] - mousePos.current[1]
                                const dist = Math.sqrt(dx * dx + dy * dy)
                                if (dist < minDist) {
                                    minDist = dist
                                    hoveredSat = { ...sat, projected, longitude, latitude } // Store extra info
                                }
                            }

                            // Determine style based on type
                            const isImportant = sat.type === 'satellite' || sat.type === 'featured'
                            // If this IS the hovered satellite (will check later, but for now just draw normally)

                            // Size
                            const size = isImportant ? 4 * scaleFactor : 1.5 * scaleFactor

                            // Color
                            let color = "#22d3ee" // Default (Background): Cyan-400
                            let size_mult = 1.0

                            if (sat.type === 'satellite') {
                                color = "#22d3ee" // Cyan-400 (Primary)
                                size_mult = 2.0
                            }
                            else if (sat.type === 'featured') {
                                color = "#22d3ee" // Cyan-400 (Featured)
                                size_mult = 1.5
                            }
                            else if (sat.type === 'debris') {
                                color = "#ef4444" // Red-500 (Debris)
                                size_mult = 1.5 // Make debris slightly larger for visibility
                            }
                            else {
                                color = "#22d3ee" // Cyan-400 (Background)
                            }

                            // Apply size multiplier to the base size
                            const finalSize = size * size_mult

                            context.beginPath()
                            context.arc(projected[0], projected[1], finalSize, 0, 2 * Math.PI)

                            // Glint/Glow effect for important ones AND debris
                            if (isImportant || sat.type === 'debris') {
                                context.shadowBlur = 10
                                context.shadowColor = color
                            }

                            context.fillStyle = color
                            context.fill()

                            context.shadowBlur = 0 // Reset

                            // Draw Label (ONLY for important ones, UNLESS hovered - we handle hovered label below)
                            if (isImportant) {
                                context.font = `bold ${10 * scaleFactor}px monospace`
                                context.fillStyle = "#ffffff"
                                context.fillText(sat.name, projected[0] + 8, projected[1] - 4)
                            }
                        }
                    }
                })
            }

            // --- DRAW HOVERED SATELLITE OVERLAY ---
            if (hoveredSat) {
                // 1. Draw Orbit Path
                const orbitPath = getOrbitPath(hoveredSat.satrec, new Date())

                context.beginPath()
                let first = true
                orbitPath.forEach(coord => {
                    const pt = projection(coord)
                    if (pt) {
                        if (first) { context.moveTo(pt[0], pt[1]); first = false; }
                        else context.lineTo(pt[0], pt[1])
                    }
                })
                context.strokeStyle = "#fbbf24" // Amber/Gold for orbit path
                context.lineWidth = 2 * scaleFactor
                context.setLineDash([5, 5]) // Dotted line
                context.stroke()
                context.setLineDash([]) // Reset

                // 2. Highlight Dot
                context.beginPath()
                context.arc(hoveredSat.projected[0], hoveredSat.projected[1], 6 * scaleFactor, 0, 2 * Math.PI)
                context.fillStyle = "#fbbf24"
                context.shadowBlur = 15
                context.shadowColor = "#fbbf24"
                context.fill()
                context.shadowBlur = 0

                // 3. Draw Label & Info Box
                const labelX = hoveredSat.projected[0] + 15
                const labelY = hoveredSat.projected[1] - 15

                // Box background
                context.fillStyle = "rgba(0, 0, 0, 0.8)"
                context.fillRect(labelX, labelY - 20, 150 * scaleFactor, 50 * scaleFactor)
                context.strokeStyle = "#fbbf24"
                context.lineWidth = 1
                context.strokeRect(labelX, labelY - 20, 150 * scaleFactor, 50 * scaleFactor)

                // Text
                context.font = `bold ${12 * scaleFactor}px monospace`
                context.fillStyle = "#fbbf24"
                context.fillText(hoveredSat.name, labelX + 10, labelY)

                context.font = `${10 * scaleFactor}px monospace`
                context.fillStyle = "#cccccc"
                context.fillText(`Lat: ${hoveredSat.latitude.toFixed(2)}°`, labelX + 10, labelY + 15)
                context.fillText(`Lng: ${hoveredSat.longitude.toFixed(2)}°`, labelX + 10, labelY + 25)
            }
        }

        const loadWorldData = async () => {
            try {
                setIsLoading(true)

                const response = await fetch(
                    "https://raw.githubusercontent.com/martynafford/natural-earth-geojson/refs/heads/master/110m/physical/ne_110m_land.json",
                )
                if (!response.ok) throw new Error("Failed to load land data")

                landFeatures = await response.json()

                // Generate dots for all land features
                let totalDots = 0
                landFeatures.features.forEach((feature: any) => {
                    const dots = generateDotsInPolygon(feature, 16)
                    dots.forEach(([lng, lat]) => {
                        allDots.push({ lng, lat, visible: true })
                        totalDots++
                    })
                })

                render()
                setIsLoading(false)
            } catch (err) {
                setError("Failed to load land map data")
                setIsLoading(false)
            }
        }

        // Set up rotation and interaction
        const rotation = [0, 0]
        let autoRotate = true
        const rotationSpeed = 0.1 // Slower rotation

        const rotate = () => {
            // Always render in the loop to animate satellites even if earth isn't rotating manually
            if (autoRotate) {
                rotation[0] += rotationSpeed
                projection.rotate(rotation as [number, number])
            }
            render()
        }

        // Auto-rotation timer
        const rotationTimer = d3.timer(rotate)

        const handleMouseDown = (event: MouseEvent) => {
            autoRotate = false
            const startX = event.clientX
            const startY = event.clientY
            const startRotation = [...rotation]

            const handleMouseMove = (moveEvent: MouseEvent) => {
                const sensitivity = 0.5
                const dx = moveEvent.clientX - startX
                const dy = moveEvent.clientY - startY

                rotation[0] = startRotation[0] + dx * sensitivity
                rotation[1] = startRotation[1] - dy * sensitivity
                rotation[1] = Math.max(-90, Math.min(90, rotation[1]))

                projection.rotate(rotation as [number, number])
                // Do NOT call render() here because the timer calls it. 
                // Just update rotation state. 
                // Actually the timer calls render() every frame, so we are good.
            }

            const handleMouseUp = () => {
                document.removeEventListener("mousemove", handleMouseMove)
                document.removeEventListener("mouseup", handleMouseUp)

                setTimeout(() => {
                    autoRotate = true
                }, 3000) // Resume after 3s
            }

            document.addEventListener("mousemove", handleMouseMove)
            document.addEventListener("mouseup", handleMouseUp)
        }

        const handleCanvasMouseMove = (event: MouseEvent) => {
            const rect = canvas.getBoundingClientRect()
            // Account for CSS transforms (scale) by calculating the ratio of logical size to bounding client size
            // canvas.width is internal size * dpr. So logical size is canvas.width / dpr.
            const dpr = window.devicePixelRatio || 1
            const logicalWidth = canvas.width / dpr
            const logicalHeight = canvas.height / dpr

            const scaleX = logicalWidth / rect.width
            const scaleY = logicalHeight / rect.height

            const x = (event.clientX - rect.left) * scaleX
            const y = (event.clientY - rect.top) * scaleY

            mousePos.current = [x, y]
            // Render handled by loop
        }

        const handleCanvasMouseLeave = () => {
            mousePos.current = null
        }

        const handleWheel = (event: WheelEvent) => {
            event.preventDefault()
            const scaleFactor = event.deltaY > 0 ? 0.9 : 1.1
            const newRadius = Math.max(radius * 0.5, Math.min(radius * 3, projection.scale() * scaleFactor))
            projection.scale(newRadius)
            // Render handled by loop
        }

        canvas.addEventListener("mousedown", handleMouseDown)
        canvas.addEventListener("mousemove", handleCanvasMouseMove)
        canvas.addEventListener("mouseleave", handleCanvasMouseLeave)
        canvas.addEventListener("wheel", handleWheel)

        // Load the world data
        loadWorldData()

        // Cleanup
        return () => {
            rotationTimer.stop()
            canvas.removeEventListener("mousedown", handleMouseDown)
            canvas.removeEventListener("mousemove", handleCanvasMouseMove)
            canvas.removeEventListener("mouseleave", handleCanvasMouseLeave)
            canvas.removeEventListener("wheel", handleWheel)
        }
    }, [width, height, satellites.length]) // Re-init if satellites count changes significantly (actually logic inside handles it)

    if (error) {
        return (
            <div className={`dark flex items-center justify-center bg-card rounded-2xl p-8 ${className}`}>
                <div className="text-center">
                    <p className="dark text-destructive font-semibold mb-2">Error loading Earth visualization</p>
                    <p className="dark text-muted-foreground text-sm">{error}</p>
                </div>
            </div>
        )
    }

    return (
        <div className={`relative ${className}`}>
            <canvas
                ref={canvasRef}
                className="w-full h-auto rounded-2xl bg-[#02040a] cursor-move"
                style={{ maxWidth: "100%", height: "auto" }}
            />
            <div className="absolute bottom-4 left-4 text-xs text-muted-foreground px-2 py-1 rounded-md bg-neutral-900/50 backdrop-blur">
                Drag to rotate • Scroll to zoom
            </div>
        </div>
    )
}
