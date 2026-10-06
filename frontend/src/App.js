import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Insights from "./pages/Insights";
import Partners from "./pages/Partners";
import Invoices from "./pages/Invoices";
import Forecast from "./pages/Forecast";
import PartnerDetails from "./pages/PartnerDetails";
import DataPipeline from "./pages/DataPipeline";
import Dashboard from "./pages/Dashboard";
import Layout from "./components/Layout";
import Chatbot from "./pages/Chatbot";
import Login from "./pages/Login";
import CashCalendar from "./pages/CashCalendar";
import NetLiquidity from "./pages/NetLiquidity";
import Home from "./pages/Home";
import ApApp from "./ap/App";

function RequireAuth() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter basename={process.env.PUBLIC_URL || "/cct"}>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route element={<RequireAuth />}>
              {/* Product home = Cash Calendar (Level B spine) */}
              <Route path="/" element={<CashCalendar />} />
              <Route path="/hub" element={<Home />} />
              <Route path="/liquidity" element={<Navigate to="/" replace />} />

              {/* AR Sensei */}
              <Route path="/ar" element={<Layout />}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="partners" element={<Partners />} />
                <Route path="partners/:partnerCode/details" element={<PartnerDetails />} />
                <Route path="insights" element={<Insights />} />
                <Route path="invoices" element={<Invoices />} />
                <Route path="forecast" element={<Forecast />} />
                <Route path="pipeline" element={<DataPipeline />} />
                <Route path="chatbot" element={<Chatbot />} />
              </Route>

              {/* AP Control Tower */}
              <Route path="/ap/*" element={<ApApp />} />
            </Route>

            <Route path="/dashboard" element={<Navigate to="/ar/dashboard" replace />} />
            <Route path="/partners" element={<Navigate to="/ar/partners" replace />} />
            <Route path="/insights" element={<Navigate to="/ar/insights" replace />} />
            <Route path="/invoices" element={<Navigate to="/ar/invoices" replace />} />
            <Route path="/forecast" element={<Navigate to="/ar/forecast" replace />} />
            <Route path="/pipeline" element={<Navigate to="/ar/pipeline" replace />} />
            <Route path="/chatbot" element={<Navigate to="/ar/chatbot" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </div>
  );
}

export default App;
