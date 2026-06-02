      document.addEventListener("DOMContentLoaded", function () {
        var chartDom = document.getElementById('student-population-chart');
        var myChart = echarts.init(chartDom);
      
        fetch('/api/student-per-course/')  // Django API endpoint
          .then(response => response.json())
          .then(data => {
            var years = ['1st Year College', '2nd Year College', '3rd Year College', '4th Year College'];
            var courses = Object.keys(data);  // Get course names
            var courseShortNames = courses.map(course => data[course].short_name);
      
            // Define color scheme
            var colors = {
              "1st Year College": "#4CAF50",
              "2nd Year College": "#FF5733",
              "3rd Year College": "#3498DB",
              "4th Year College": "#F1C40F"
            };
      
            // Organize data for each year level
            var timelineData = years.map(year => ({
              title: { 
                text: `${year} Student Population`,
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'bold' } // Better font for title
              },
              series: [
                {
                  name: year,
                  type: 'bar',
                  barWidth: '50%',  // Adjust bar width for better visibility
                  data: courses.map(course => data[course].year_levels[year] || 0),  // Fill missing values with 0
                  itemStyle: { color: colors[year] },
                  label: {
                    show: true,
                    position: 'top',
                    color: '#333', // Display numbers on top of bars
                    fontSize: 12
                  }
                }
              ]
            }));
      
            var option = {
              baseOption: {
                timeline: {
                  axisType: 'category',
                  autoPlay: false, // Prevent auto-slide so users control navigation
                  playInterval: 2500,
                  data: years
                },
                tooltip: {
                  trigger: 'axis',
                  axisPointer: { type: 'shadow' },
                  backgroundColor: 'rgba(0,0,0,0.8)',
                  textStyle: { color: '#fff' }
                },
                legend: {
                  data: years,
                  top: 20,
                  left: 'center',
                  textStyle: { color: '#6c757d', fontSize: 12 }
                },
                xAxis: {
                  type: 'category',
                  data: courseShortNames,  // Courses on X-axis
                  axisLabel: { 
                    color: '#6c757d',
                    fontSize: 12,
                    interval: 0,  // Prevent skipping labels
                    rotate: 25  // Adjust rotation for better spacing
                  },
                  axisTick: { alignWithLabel: true }
                },
                yAxis: {
                  type: 'value',
                  axisLabel: { color: '#6c757d', fontSize: 12 },
                  splitLine: { lineStyle: { color: '#e0e0e0' } }
                },
                grid: {
                  left: '5%', right: '5%', bottom: '15%', containLabel: true  // Adjust grid for better spacing
                },
                series: []
              },
              options: timelineData
            };
      
            myChart.setOption(option);
          })
          .catch(error => console.error("Error loading student population data:", error));
      });
      
    

        document.addEventListener("DOMContentLoaded", function () {
          var chartDom = document.getElementById('student-population-subject-chart');
          var myChart = echarts.init(chartDom);
        
          fetch('/api/student-per-subject/')  // Update with the correct Django API URL
            .then(response => response.json())
            .then(data => {
              var subjects = data.subjects;  // Extract subject names
              var studentCounts = data.student_counts;  // Extract student count per subject
        
              // Define an array of different colors
              var colors = [
                "#4CAF50", "#FF5733", "#3498DB", "#F1C40F", "#9B59B6",
                "#E74C3C", "#1ABC9C", "#2ECC71", "#F39C12", "#D35400"
              ];
        
              // Ensure each subject gets a unique color
              var colorMapping = subjects.reduce((acc, subject, index) => {
                acc[subject] = colors[index % colors.length];
                return acc;
              }, {});
        
              var option = {
                tooltip: {
                  trigger: 'axis',
                  axisPointer: { type: 'shadow' }
                },
                legend: {
                  data: subjects,
                  textStyle: { color: '#6c757d' }
                },
                xAxis: {
                  type: 'category',
                  data: subjects,  // Set subjects on X-axis
                  axisLabel: { color: '#6c757d', rotate: 30 } // Rotates labels to prevent overlap
                },
                yAxis: {
                  type: 'value',
                  axisLabel: { color: '#6c757d' },
                  splitLine: { lineStyle: { color: '#e0e0e0' } }
                },
                series: [{
                  name: 'Students',
                  type: 'bar',
                  data: studentCounts,  // Assign student counts to the bars
                  itemStyle: {
                    color: function (params) {
                      return colorMapping[subjects[params.dataIndex]];
                    }
                  }
                }]
              };
        
              myChart.setOption(option);
            })
            .catch(error => console.error("Error loading student population data:", error));
        });                
      

      document.addEventListener("DOMContentLoaded", function () {
        let chartDom = document.getElementById('feedback-score-chart');
    
        if (!chartDom) {
            return;
        }
    
        fetch('/api/get_all_teachers_average_ratings_json/')  
            .then(response => response.json())
            .then(data => {
    
                var myChart = echarts.init(chartDom);
    
                var chartData = data.ratings.map(item => ({
                    value: item.average_rating,
                    name: `${item.subject_name} (${item.teacher_name})`
                }));
    
                let option = {
                    title: {
                        text: "Teacher Feedback Score", // ✅ Add Chart Title Here
                        left: "center",
                        textStyle: {
                            fontSize: 18,
                            fontWeight: "bold",
                            color: "#2c3e50"
                        }
                    },
                    tooltip: {
                        trigger: 'item'
                    },
                    series: [
                        {
                            name: 'Feedback Score',
                            type: 'pie',
                            radius: ['30%', '70%'],
                            center: ['50%', '50%'],
                            label: {
                                position: 'outside',
                                alignTo: 'labelLine',
                                formatter: '{b}: {c}',
                                color: '#6c757d'
                            },
                            labelLine: {
                                show: true,
                                length: 8,
                                length2: 15,
                                smooth: true
                            },
                            data: chartData,  // Use the API data
                            emphasis: {
                                itemStyle: {
                                    shadowBlur: 10,
                                    shadowOffsetX: 0,
                                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                                }
                            }
                        }
                    ]
                };
    
                myChart.setOption(option);
            })
            .catch(error => console.error('Error fetching ratings data:', error));
    });
    
    

      document.addEventListener("DOMContentLoaded", function () {
          let chartDom = document.getElementById('activity-chart');
    
          // ✅ Check if the chart container exists before running script
          if (!chartDom) {
              return;
          }
    
          // ✅ Fetch the activities per subject from the new API
          fetch('/api/student_activities_json/')
              .then(response => response.json())
              .then(data => {
    
                  if (!Array.isArray(data) || data.length === 0) {
                      chartDom.innerHTML = "<p style='text-align:center; color:#6c757d; font-size:16px;'>No activity data available.</p>";
                      return;
                  }
    
                  let subjectLabels = data.map(subject => subject.subject__subject_name);
                  let activityCounts = data.map(subject => subject.activity_count);
    
                  var myChart = echarts.init(chartDom);
    
                  let option = {
                      title: {
                          text: "Your Activities Per Subject",
                          left: "center",
                          textStyle: {
                              fontSize: 18,
                              fontWeight: "bold",
                              color: "#2c3e50"
                          }
                      },
                      tooltip: { trigger: 'axis' },
                      xAxis: {
                          type: 'category',
                          data: subjectLabels
                      },
                      yAxis: {
                          type: 'value',
                          min: 0
                      },
                      series: [
                          {
                              name: 'Activity Count',
                              type: 'bar',
                              data: activityCounts,
                              color: '#2c7be5'
                          }
                      ]
                  };
    
                  console.log("DEBUG: Setting chart options:", option);
                  myChart.setOption(option);
              })
              .catch(error => console.error('Error fetching student activity data:', error));
      });
    

      document.addEventListener("DOMContentLoaded", function () {
        fetch('/api/student_last_login_list/')
          .then(response => {
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
          })
          .then(data => {
            // Validate data structure
            if (!data || !data.daily_logins || !data.daily_logins.labels || !data.daily_logins.data) {
              console.error('Invalid data structure received:', data);
              return;
            }

            var chartDom = document.getElementById('active-students-chart');
            if (!chartDom) {
              console.error('Chart container not found');
              return;
            }

            var myChart = echarts.init(chartDom);
    
            var option = {
              tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross' }
              },
              xAxis: {
                type: 'category',
                data: data.daily_logins.labels,
                axisLabel: { color: '#6c757d' }
              },
              yAxis: {
                type: 'value',
                axisLabel: { color: '#6c757d' },
                splitLine: { lineStyle: { color: '#e0e0e0' } }
              },
              series: [{
                name: 'Daily Logins',
                type: 'line',
                smooth: true,
                data: data.daily_logins.data,
                lineStyle: { width: 2, color: 'rgba(255, 87, 34, 1)' },
                areaStyle: {
                  color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(255, 87, 34, 0.6)' },
                    { offset: 1, color: 'rgba(255, 87, 34, 0.1)' }
                  ])
                },
                itemStyle: { color: 'rgba(255, 87, 34, 1)' }
              }]
            };
    
            myChart.setOption(option);
          })
          .catch(error => console.error('Error fetching login data:', error));
      });
    