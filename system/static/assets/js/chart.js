$(document).ready(function() {
	
	// Bar Chart

	var barChartData = {
		labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
		datasets: [{
			label: 'Dataset 1',
			backgroundColor: 'rgba(0, 158, 251, 0.5)',
			borderColor: 'rgba(0, 158, 251, 1)',
			borderWidth: 1,
			data: [0, 0, 0, 0, 0, 0, 0]
		}, {
			label: 'Dataset 2',
			backgroundColor: 'rgba(255, 188, 53, 0.5)',
			borderColor: 'rgba(255, 188, 53, 1)',
			borderWidth: 1,
			data: [0, 0, 0, 0, 0, 0, 0]
		}]
	};

	var ctx = document.getElementById('bargraph').getContext('2d');
	window.myBar = new Chart(ctx, {
		type: 'bar',
		data: barChartData,
		options: {
			responsive: true,
			legend: {
				display: false,
			}
		}
	});

	// Line Chart

	var lineChartData = {
		labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
		datasets: [{
			label: "My First dataset",
			backgroundColor: "rgba(0, 158, 251, 0.5)",
			data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
		}, {
		label: "My Second dataset",
		backgroundColor: "rgba(255, 188, 53, 0.5)",
		fill: true,
		data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
		}]
	};
	
	var linectx = document.getElementById('linegraph').getContext('2d');
	window.myLine = new Chart(linectx, {
		type: 'line',
		data: lineChartData,
		options: {
			responsive: true,
			legend: {
				display: false,
			},
			tooltips: {
				mode: 'index',
				intersect: false,
			}
		}
	});
	
	// Bar Chart 2
	
    barChart();
    
    $(window).resize(function(){
        barChart();
    });
    
    function barChart(){
        $('.bar-chart').find('.item-progress').each(function(){
            var itemProgress = $(this),
            itemProgressWidth = $(this).parent().width() * ($(this).data('percent') / 100);
            itemProgress.css('width', itemProgressWidth);
        });
    };
});