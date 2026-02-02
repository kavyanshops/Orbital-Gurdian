import { Shield } from "lucide-react";
import LiveFeed from "./components/LiveFeed";
import Dashboard from "./components/Dashboard";

export default function App() {
  return (
    <div className="min-h-screen w-full bg-black text-white p-4 md:p-8 font-sans selection:bg-cyan-500/30">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <header className="flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Orbital Guardian</h1>
              <p className="text-xs text-muted-foreground">Advanced Collision Avoidance System</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>v2.4.0</span>
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span>System Online</span>
          </div>
        </header>

        {/* Live Feed Section */}
        <LiveFeed />

        {/* Main Analysis Dashboard */}
        <Dashboard />
      </div>
    </div>
  );
}
