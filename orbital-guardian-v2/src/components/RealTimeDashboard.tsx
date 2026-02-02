import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Search, RefreshCw, Satellite, ShieldAlert, Activity } from "lucide-react";

interface StatusResponse {
    status: string;
    timestamp: string;
    monitored_satellites: number;
    recent_events: number;
}

interface SatelliteData {
    norad_id: number;
    name: string;
    epoch: string;
}

interface ConjunctionEvent {
    event_id: string;
    primary_id: number;
    secondary_id: number;
    tca: string;
    miss_distance: number;
    probability: number;
    risk_level: string;
}

export default function RealTimeDashboard() {
    const [status, setStatus] = useState<StatusResponse | null>(null);
    const [satellites, setSatellites] = useState<SatelliteData[]>([]);
    const [events, setEvents] = useState<ConjunctionEvent[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [searchId, setSearchId] = useState("");

    const API_URL = "http://localhost:8000/api";

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${API_URL}/status`);
            if (res.ok) setStatus(await res.json());
        } catch (e) {
            console.error("Failed to fetch status", e);
        }
    };

    const fetchSatellites = async () => {
        try {
            const res = await fetch(`${API_URL}/satellites`);
            if (res.ok) setSatellites(await res.json());
        } catch (e) {
            console.error("Failed to fetch satellites", e);
        }
    };

    const screenSatellite = async () => {
        if (!searchId) return;
        setIsLoading(true);
        try {
            const res = await fetch(`${API_URL}/conjunctions/screen/${searchId}`, {
                method: "POST"
            });
            if (res.ok) {
                const data = await res.json();
                const newEvents: ConjunctionEvent[] = data.events.map((e: any) => ({
                    event_id: e.event_id,
                    primary_id: e.primary.norad_id,
                    secondary_id: e.secondary.norad_id,
                    tca: e.tca,
                    miss_distance: e.miss_distance,
                    probability: e.probability,
                    risk_level: e.risk_level
                }));
                setEvents(prev => [...prev, ...newEvents]);
                fetchStatus(); // Update counts
                setLastUpdated(new Date());
            }
        } catch (e) {
            console.error("Screening failed", e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        fetchSatellites();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-300">

            {/* Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-6 rounded-2xl border border-green-500/30 bg-green-950/20 flex flex-col items-center justify-center text-center">
                    <Activity className="w-8 h-8 text-green-400 mb-2" />
                    <div className="text-2xl font-bold text-white">{status?.status === "running" ? "ONLINE" : "OFFLINE"}</div>
                    <div className="text-xs text-green-400">System Status</div>
                </div>
                <div className="p-6 rounded-2xl border border-white/10 bg-card/50 flex flex-col items-center justify-center text-center">
                    <Satellite className="w-8 h-8 text-cyan-400 mb-2" />
                    <div className="text-2xl font-bold text-white">{status?.monitored_satellites ?? 0}</div>
                    <div className="text-xs text-slate-400">Monitored Assets</div>
                </div>
                <div className="p-6 rounded-2xl border border-white/10 bg-card/50 flex flex-col items-center justify-center text-center">
                    <ShieldAlert className="w-8 h-8 text-orange-400 mb-2" />
                    <div className="text-2xl font-bold text-white">{status?.recent_events ?? 0}</div>
                    <div className="text-xs text-slate-400">Active Threats</div>
                </div>
            </div>

            {/* Action Bar */}
            <div className="p-6 rounded-xl border border-white/10 bg-card/30 flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="flex gap-2 w-full md:w-auto">
                    <input
                        type="text"
                        placeholder="NORAD ID (e.g., 25544)"
                        value={searchId}
                        onChange={(e) => setSearchId(e.target.value)}
                        className="px-4 py-2 rounded-lg bg-black/40 border border-white/10 text-white outline-none focus:border-cyan-400"
                    />
                    <button
                        onClick={screenSatellite}
                        disabled={isLoading || !searchId}
                        className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-bold disabled:opacity-50 flex items-center gap-2"
                    >
                        <Search className="w-4 h-4" />
                        {isLoading ? "Screening..." : "Screen Threats"}
                    </button>
                </div>
                <div className="text-xs text-slate-500">
                    Real-time screening powered by Foster-1992 Algorithm
                </div>
            </div>

            {/* Events List */}
            <div className="rounded-xl border border-white/10 bg-black/20 overflow-hidden">
                <div className="px-6 py-4 border-b border-white/10 bg-white/5 font-semibold text-slate-300">
                    Live Conjunction Events
                </div>
                {events.length === 0 ? (
                    <div className="p-8 text-center text-slate-500">
                        No active threats detected.
                    </div>
                ) : (
                    <table className="w-full text-sm text-left">
                        <thead className="bg-white/5 text-slate-400 text-xs uppercase">
                            <tr>
                                <th className="px-6 py-3">Risk Level</th>
                                <th className="px-6 py-3">Event ID</th>
                                <th className="px-6 py-3">TCA (UTC)</th>
                                <th className="px-6 py-3">Miss Dist</th>
                                <th className="px-6 py-3">Prob</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/10">
                            {events.map(evt => (
                                <tr key={evt.event_id} className="hover:bg-white/5">
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${evt.risk_level === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                                            {evt.risk_level}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 font-mono">{evt.event_id.substring(0, 12)}...</td>
                                    <td className="px-6 py-4">{new Date(evt.tca).toLocaleString()}</td>
                                    <td className="px-6 py-4 font-mono">{evt.miss_distance.toFixed(3)} m</td>
                                    <td className="px-6 py-4">{evt.probability.toExponential(2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

        </div>
    );
}
