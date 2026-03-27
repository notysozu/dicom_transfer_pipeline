function AppShell({ children }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>DICOM UI</h1>
        <p>Clinical Imaging Transfer Control Plane</p>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}

export default AppShell;
