const { invoke } = window.__TAURI__.tauri;

// Send commands to Python backend
async function sendToPython(action, payload) {
  try {
    await invoke('send_to_python', { action, payload });
  } catch (error) {
    console.error('Failed to send to Python:', error);
  }
}

// Make it globally available
window.sendToPython = sendToPython;

// Poll Python for state updates every second
async function pollPythonState() {
  try {
    const response = await fetch('http://localhost:8765/state');
    const state = await response.json();

    // Update UI based on state
    window.updateStatus(state.isRunning);

    if (state.waterPoint) {
      window.updatePointStatus('waterPoint', state.waterPoint.x, state.waterPoint.y);
    }

    // Update other points...

  } catch (error) {
    console.error('Failed to poll state:', error);
  }
}

// Start polling when app loads
setInterval(pollPythonState, 1000);