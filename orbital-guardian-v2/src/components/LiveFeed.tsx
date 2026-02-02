import { useEffect, useState } from "react";
import RotatingEarth from "./ui/wireframe-dotted-globe";
import { ArrowRight, Satellite, ShieldCheck } from "lucide-react";

interface SatelliteData {
    name: string;
    line1: string;
    line2: string;
    type?: 'satellite' | 'debris' | 'featured' | 'background';
}

export default function LiveFeed() {
    const [satellites, setSatellites] = useState<SatelliteData[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch("http://localhost:5050/api/live-satellites");
                if (res.ok) {
                    const json = await res.json();
                    const sats: SatelliteData[] = [];
                    if (json.satellite) sats.push(json.satellite);
                    if (json.debris) sats.push(...json.debris);
                    setSatellites(sats);
                }
            } catch (e) {
                console.error("Failed to fetch live data", e);
            }
        };

        fetchData();
    }, []);

    return (
        <div className="relative w-full h-[700px] overflow-hidden rounded-2xl border border-white/10 bg-[#02040a] shadow-2xl shadow-cyan-900/20 group">

            {/* Background/Globe Layer */}
            <div className="absolute inset-0 flex items-center justify-center opacity-80 group-hover:opacity-100 transition-opacity duration-1000">
                <RotatingEarth width={1200} height={1000} className="scale-110" satellites={satellites} />
            </div>

            {/* Gradient Overlay for Text Readability */}
            <div className="absolute inset-0 bg-gradient-to-r from-black/90 via-black/40 to-transparent pointer-events-none"></div>

            {/* Hero Content Overlay */}
            <div className="absolute inset-0 flex flex-col justify-center px-6 md:px-12 z-20 pointer-events-none">
                <div className="max-w-2xl space-y-6 pointer-events-auto">

                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/50 border border-cyan-500/30 backdrop-blur-md">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                        </span>
                        <span className="text-xs font-medium text-cyan-400 tracking-wider">LIVE SYSTEM ONLINE</span>
                    </div>

                    {/* Title */}
                    <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white">
                        <span className="block text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400">Orbital</span>
                        <span className="block text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600">Guardian</span>
                    </h1>

                    {/* Subtitle */}
                    <p className="text-base md:text-lg text-slate-400 max-w-lg leading-relaxed">
                        Real-time space debris tracking and collision avoidance system.
                        Protecting <span className="text-white font-medium">10,000+ satellites</span> with sub-kilometer precision using advanced autonomous agents.
                    </p>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-3 gap-4 md:gap-8 py-6 border-t border-white/10">
                        <div>
                            <div className="text-xl md:text-2xl font-bold text-white font-mono">{satellites.length > 0 ? satellites.length : '...'}</div>
                            <div className="text-[10px] md:text-xs text-slate-500 uppercase tracking-wider mt-1">Objects Live</div>
                        </div>
                        <div>
                            <div className="text-xl md:text-2xl font-bold text-cyan-400 font-mono">99.9%</div>
                            <div className="text-[10px] md:text-xs text-slate-500 uppercase tracking-wider mt-1">Accuracy</div>
                        </div>
                        <div>
                            <div className="text-xl md:text-2xl font-bold text-white font-mono">24/7</div>
                            <div className="text-[10px] md:text-xs text-slate-500 uppercase tracking-wider mt-1">Monitoring</div>
                        </div>
                    </div>

                    {/* CTA Buttons */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 pt-4">
                        <button onClick={() => document.getElementById('dashboard-section')?.scrollIntoView({ behavior: 'smooth' })}
                            className="w-full sm:w-auto px-8 py-4 rounded-full bg-gradient-to-r from-cyan-600 to-blue-700 text-white font-semibold hover:scale-105 transition-transform flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/50">
                            Launch Analysis <ArrowRight className="w-4 h-4" />
                        </button>
                        <button className="w-full sm:w-auto px-8 py-4 rounded-full bg-white/5 border border-white/10 text-white font-semibold hover:bg-white/10 transition-colors backdrop-blur-sm">
                            View Documentation
                        </button>
                    </div>
                </div>
            </div>

            {/* Active Protection Card (Top Right) - Hidden on mobile */}
            <div className="hidden md:block absolute top-8 right-8 p-5 rounded-xl bg-gradient-to-br from-black/60 to-black/40 border border-emerald-500/30 backdrop-blur-md w-72 animate-in slide-in-from-right duration-1000 shadow-[0_0_30px_-10px] shadow-emerald-500/20 hover:border-emerald-500/50 transition-colors z-20">
                <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_10px] shadow-emerald-500/20">
                        <ShieldCheck className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div>
                        <div className="text-xs text-emerald-200/70 font-medium tracking-wider uppercase mb-0.5">System Status</div>
                        <div className="text-lg font-bold text-white tracking-tight">Active Protection</div>
                    </div>
                </div>
            </div>

            {/* Primary Target Card (Bottom Right) - Hidden on mobile */}
            <div className="hidden md:block absolute bottom-8 right-8 p-5 rounded-xl bg-gradient-to-br from-black/60 to-black/40 border border-cyan-500/30 backdrop-blur-md w-72 animate-in slide-in-from-right duration-1000 delay-200 shadow-[0_0_30px_-10px] shadow-cyan-500/20 hover:border-cyan-500/50 transition-colors z-20">
                <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20 shadow-[0_0_10px] shadow-cyan-500/20">
                        <Satellite className="w-6 h-6 text-cyan-400" />
                    </div>
                    <div>
                        <div className="text-xs text-cyan-200/70 font-medium tracking-wider uppercase mb-0.5">Primary Target</div>
                        <div className="text-lg font-bold text-white tracking-tight">ISS (ZARYA)</div>
                    </div>
                </div>
            </div>

        </div>
    );
}
