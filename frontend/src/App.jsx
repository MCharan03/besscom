import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar  from './components/TopBar';
import CommandCenter  from './pages/CommandCenter';
import DemandForecast from './pages/DemandForecast';
import AnomalyAlerts  from './pages/AnomalyAlerts';
import FeederMapPage  from './pages/FeederMapPage';
import AuditLog       from './pages/AuditLog';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <div className="main-content">
          <TopBar />
          <Routes>
            <Route path="/"         element={<CommandCenter />} />
            <Route path="/forecast" element={<DemandForecast />} />
            <Route path="/alerts"   element={<AnomalyAlerts />} />
            <Route path="/map"      element={<FeederMapPage />} />
            <Route path="/audit"    element={<AuditLog />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
