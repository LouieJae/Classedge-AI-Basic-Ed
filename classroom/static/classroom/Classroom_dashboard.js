        const tableBody = document.getElementById('classroomTableBody');

        // Fetch data from the API
        fetch('/classroom_mode/')
          .then(response => {
            if (!response.ok) {
              throw new Error('Network response was not ok');
            }
            return response.json();
          })
          .then(data => {
            // Populate the table with aggregated data
            data.forEach(session => {
              const row = document.createElement('tr');

              row.innerHTML = `
                <td>${session.subject}</td>
                <td>${session.teacher}</td>
                <td>${session.date}</td>
                <td>${session.total_time}</td>
              `;

              tableBody.appendChild(row);
            });
          })
          .catch(error => {
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="4" class="text-center text-danger">Failed to load data</td>`;
            tableBody.appendChild(row);
          });
      