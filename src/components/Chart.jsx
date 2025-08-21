// src/components/Chart.jsx
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

const EChartsComponent = ({ option, style = { height: '400px', width: '100%' } }) => {
    const chartRef = useRef(null);
    let chartInstance = null;

    useEffect(() => {
        // Initialize chart
        if (chartRef.current) {
            chartInstance = echarts.init(chartRef.current);
            chartInstance.setOption(option);
        }

        // Handle resize
        const resizeHandler = () => {
            chartInstance?.resize();
        };
        window.addEventListener('resize', resizeHandler);

        // Clean up
        return () => {
            chartInstance?.dispose();
            window.removeEventListener('resize', resizeHandler);
        };
    }, [option]);

    return <div ref={chartRef} style={style} />;
};

// Example usage with a simple line chart
const Chart = () => {
    const chartOption = {
        title: {
            text: 'Monthly Revenue & Profit'
        },
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: ['Revenue', 'Profit']
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        },
        yAxis: {
            type: 'value'
        },
        series: [
            {
                name: 'Revenue',
                type: 'line',
                data: [120, 170, 140, 190, 220, 250]
            },
            {
                name: 'Profit',
                type: 'line',
                data: [45, 60, 52, 75, 95, 110]
            }
        ]
    };

    return <EChartsComponent option={chartOption} />;
};

export default Chart;