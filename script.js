Chart.defaults.global.defaultFontFamily = 'Roboto';
Chart.defaults.global.defaultFontColor = '#333';

function makeChart(animals) {
  var animalname = animals.map(function(d) {return d.name            });
  var weeksData = animals.map(function(d) {return +d.age_upon_outcome_in_weeks
});
  var animaltype = animals.map(function(d) {return d.animal_type
 === 'Cat' ? '#F15F36' : '#19A0AA';});

  var chart = new Chart('chart', {
    type: 'line',
    options: {
      maintainAspectRatio: false,
      legend: {
        display: false
      },
      scales: {
        xAxes: [
          {
            scaleLabel: {
              display: true,
              labelString: 'Age of Cats and Dogs in Weeks',
              fontSize: 16
            }
          }
        ],
        yAxes: [ {
                type: 'linear',
                ticks: {
                    beginAtZero: true,
                    min : 0,
                    max : 1100,
                    }
                } ]
      }
    },
    data: {
      labels: animalname,
      datasets: [
        {
          data: weeksData,
          backgroundColor: animaltype
        }
      ]
    }
  })
}

// Request data using D3
d3.csv('https://raw.githubusercontent.com/daimon2008/Capstone/master/docs/aac_shelter_outcomes(2).csv')
  .then(makeChart);