import { ref } from 'vue';
import Chart from 'chart.js/auto';

/**
 * Composable for managing Chart.js charts
 * Handles initialization, updating, and cleanup of SNMP protocol charts
 */
export function useCharts() {
  // Chart instances
  let messageTypeChart: any = null;
  let versionChart: any = null;

  // Canvas references
  const messageCanvas = ref<HTMLCanvasElement>();
  const versionCanvas = ref<HTMLCanvasElement>();

  /**
   * Initialize both message type and version charts
   * @returns {boolean} Success status
   */
  function initCharts(): boolean {
    if (!messageCanvas.value || !versionCanvas.value) {
      console.warn('Canvas elements not ready');
      return false;
    }

    try {
      const messageCtx = messageCanvas.value.getContext('2d');
      const versionCtx = versionCanvas.value.getContext('2d');
      if (!messageCtx || !versionCtx) {
        console.warn('Failed to get canvas contexts');
        return false;
      }

      messageTypeChart = new Chart(messageCtx, {
        type: 'doughnut',
        data: {
          labels: ['GET', 'SET', 'GETNEXT', 'GETBULK'],
          datasets: [
            {
              data: [0, 0, 0, 0],
              backgroundColor: ['#3B82F6', '#6366F1', '#EC4899', '#10B981'],
              borderColor: '#FFFFFF',
              borderWidth: 3,
              hoverOffset: 8,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                color: '#1F2937',
                padding: 15,
                font: { size: 12, weight: 'bold' },
                usePointStyle: true,
              },
            },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              titleColor: 'white',
              bodyColor: 'white',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              callbacks: {
                label(context: any) {
                  const total = context.dataset.data.reduce(
                    (a: number, b: number) => a + b,
                    0,
                  );
                  const percentage =
                    total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                  return `${context.label}: ${context.parsed} (${percentage}%)`;
                },
              },
            },
          },
          cutout: '60%',
        },
      });

      versionChart = new Chart(versionCtx, {
        type: 'doughnut',
        data: {
          labels: ['SNMP v1', 'SNMP v2c', 'SNMP v3'],
          datasets: [
            {
              data: [0, 0, 0],
              backgroundColor: ['#F59E0B', '#8B5CF6', '#EF4444'],
              borderColor: '#FFFFFF',
              borderWidth: 3,
              hoverOffset: 8,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                color: '#1F2937',
                padding: 15,
                font: { size: 12, weight: 'bold' },
                usePointStyle: true,
              },
            },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              titleColor: 'white',
              bodyColor: 'white',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              callbacks: {
                label(context: any) {
                  const total = context.dataset.data.reduce(
                    (a: number, b: number) => a + b,
                    0,
                  );
                  const percentage =
                    total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                  return `${context.label}: ${context.parsed} (${percentage}%)`;
                },
              },
            },
          },
          cutout: '60%',
        },
      });

      console.log('Charts initialized successfully');
      return true;
    } catch (error) {
      console.error('Failed to initialize charts:', error);
      return false;
    }
  }

  /**
   * Update chart data with new statistics
   * @param {any} messageTypeStats - Message type statistics (get, set, getnext, getbulk)
   * @param {any} protocolStats - Protocol version statistics (v1, v2c, v3)
   */
  function updateCharts(messageTypeStats: any, protocolStats: any): void {
    try {
      if (!messageTypeChart || !versionChart) {
        console.warn('Charts not initialized, skipping update');
        return;
      }

      // Update message type chart
      if (
        messageTypeChart.data &&
        messageTypeChart.data.datasets &&
        messageTypeChart.data.datasets[0]
      ) {
        messageTypeChart.data.datasets[0].data = [
          messageTypeStats.get || 0,
          messageTypeStats.set || 0,
          messageTypeStats.getnext || 0,
          messageTypeStats.getbulk || 0,
        ];
        messageTypeChart.update('none'); // Use 'none' animation mode for better performance
      }

      // Update version chart
      if (
        versionChart.data &&
        versionChart.data.datasets &&
        versionChart.data.datasets[0]
      ) {
        versionChart.data.datasets[0].data = [
          protocolStats.v1 || 0,
          protocolStats.v2c || 0,
          protocolStats.v3 || 0,
        ];
        versionChart.update('none'); // Use 'none' animation mode for better performance
      }

      console.log('Charts updated successfully with data:', {
        messageTypeData: [
          messageTypeStats.get || 0,
          messageTypeStats.set || 0,
          messageTypeStats.getnext || 0,
          messageTypeStats.getbulk || 0,
        ],
        versionData: [
          protocolStats.v1 || 0,
          protocolStats.v2c || 0,
          protocolStats.v3 || 0,
        ],
      });
    } catch (error) {
      console.error('Error updating charts:', error);
    }
  }

  /**
   * Destroy and cleanup chart instances
   */
  function destroyCharts(): void {
    if (messageTypeChart) {
      messageTypeChart.destroy();
      messageTypeChart = null;
    }
    if (versionChart) {
      versionChart.destroy();
      versionChart = null;
    }
    console.log('Charts destroyed');
  }

  /**
   * Reset chart data to zero values
   */
  function resetCharts(): void {
    try {
      if (
        messageTypeChart &&
        messageTypeChart.data &&
        messageTypeChart.data.datasets
      ) {
        messageTypeChart.data.datasets[0].data = [0, 0, 0, 0];
        messageTypeChart.update('none');
      }
      if (versionChart && versionChart.data && versionChart.data.datasets) {
        versionChart.data.datasets[0].data = [0, 0, 0];
        versionChart.update('none');
      }
      console.log('Charts reset to zero values');
    } catch (error) {
      console.error('Error resetting charts:', error);
    }
  }

  /**
   * Check if charts are initialized
   */
  function areChartsInitialized(): boolean {
    return messageTypeChart !== null && versionChart !== null;
  }

  /**
   * Get the current chart instances
   */
  function getChartInstances() {
    return {
      messageTypeChart,
      versionChart,
    };
  }

  return {
    // Canvas references
    messageCanvas,
    versionCanvas,

    // Methods
    initCharts,
    updateCharts,
    destroyCharts,
    resetCharts,
    areChartsInitialized,
    getChartInstances,
  };
}
