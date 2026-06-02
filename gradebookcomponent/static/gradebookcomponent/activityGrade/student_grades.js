    $(function () {
        const userRole = ($('#user-role').val() || '').toLowerCase();
        const userId = $('#user-id').val();
        const isTeacher = userRole === 'teacher' || userRole === 'admin';

        let transmutationRules = [];
        let selectedSemester = $('#semester option:selected').text();
        let selectedSubject = '';
        let lastTermInfo = {};
        let lastVisibilityByTerm = {};

        function toast(icon, message) {
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: icon || 'success',
                title: message,
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        }

        $.ajax({
            url: '/api/transmutation_rules/',
            method: 'GET',
            success: (data) => { transmutationRules = data.rules || []; },
            error: () => toast('error', 'Failed to fetch transmutation rules.')
        });

        function applyTransmutation(grade) {
            if (grade === null || grade === undefined || grade === '--') return '--';
            const g = parseFloat(grade);
            if (isNaN(g)) return '--';
            for (const rule of transmutationRules) {
                if (g >= rule.min_grade && g <= rule.max_grade) return rule.transmuted_value;
            }
            return g;
        }

        function gradeClass(grade, passing) {
            if (grade === null || grade === undefined || grade === '--') return 'muted';
            const g = parseFloat(grade);
            if (isNaN(g)) return 'muted';
            return g >= passing ? 'pass' : 'fail';
        }

        function fmtGrade(g) {
            if (g === null || g === undefined || g === '--') return '--';
            const n = parseFloat(g);
            if (isNaN(n)) return '--';
            return n.toFixed(2);
        }

        function clearStates() {
            $('#grades-empty, #grades-hidden, #grades-no-data').hide();
            $('#grades-table').hide();
        }

        function showState(which) {
            clearStates();
            $('#' + which).show();
        }

        function fetchSubjects(semesterId) {
            $('#subject').html('<option value="" selected disabled>Select Subject</option>');
            if (!semesterId) return;
            $.ajax({
                url: '/api/subjects/',
                data: { semester: semesterId },
                success: (data) => {
                    if (data && data.length) {
                        data.forEach(s => {
                            const label = `${s.subject_name || ''}${s.subject_type ? ' - (' + s.subject_type + ')' : ''}`;
                            $('#subject').append(`<option value="${s.id}">${label}</option>`);
                        });
                    } else {
                        $('#subject').append('<option value="">No subjects available</option>');
                    }
                },
                error: (xhr) => toast('error', `Failed to fetch subjects (${xhr.status}).`)
            });
        }

        function buildHeader(terms, passing) {
            const termHeaders = terms.map(term => {
                const visible = lastVisibilityByTerm[term] !== false;
                let toggle = '';
                if (isTeacher) {
                    const icon = visible ? 'fa-eye' : 'fa-eye-slash';
                    const title = visible ? 'Visible — click to hide this term' : 'Hidden — click to show this term';
                    toggle = `<button class="sg-term-toggle" data-term="${term}" title="${title}" type="button"><i class="fas ${icon}"></i></button>`;
                }
                const badge = isTeacher
                    ? `<span class="badge ${visible ? 'bg-success-soft' : 'bg-secondary-soft'} ms-1">${visible ? 'Visible' : 'Hidden'}</span>`
                    : '';
                return `<th class="sg-term-th">${term}${badge}${toggle}</th>`;
            }).join('');

            return `
                <tr>
                    <th rowspan="2" class="sg-sticky">Student</th>
                    ${termHeaders}
                    <th rowspan="2" style="min-width:120px;">Final Grade</th>
                    <th rowspan="2" style="min-width:120px;">Transmuted</th>
                </tr>
                <tr>
                    ${terms.map(() => `<th class="text-muted small fw-normal">Passing ${passing}</th>`).join('')}
                </tr>
            `;
        }

        function termCell(termData, passing) {
            if (!termData || termData.total_grade === null || termData.total_grade === undefined) {
                return `<td><span class="sg-grade-pill muted">--</span></td>`;
            }
            const g = termData.total_grade;
            return `<td><span class="sg-grade-pill ${gradeClass(g, passing)}">${fmtGrade(g)}</span></td>`;
        }

        function fetchGrades() {
            const semesterId = $('#semester').val();
            const subjectId = $('#subject').val();

            if (!semesterId || !subjectId) {
                showState('grades-empty');
                return;
            }

            selectedSemester = $('#semester option:selected').text();
            selectedSubject = $('#subject option:selected').text();

            $.ajax({
                url: '/api/student-activity-summary/',
                data: { semester: semesterId, subject: subjectId },
                success: (data) => {
                    if (!data || !Object.keys(data).length) {
                        showState('grades-no-data');
                        return;
                    }

                    let entries = Object.entries(data);
                    if (userRole === 'student') {
                        entries = entries.filter(([_, d]) => d.student_id == userId);
                    }
                    if (!entries.length) {
                        showState('grades-no-data');
                        return;
                    }

                    const sample = entries[0][1];
                    const terms = sample.term_grades ? Object.keys(sample.term_grades) : [];
                    lastTermInfo = sample.term_info || {};
                    lastVisibilityByTerm = {};
                    terms.forEach(t => {
                        const v = sample.term_grades[t] && sample.term_grades[t].visibility;
                        lastVisibilityByTerm[t] = v !== false;
                    });

                    if (userRole === 'student') {
                        const allHidden = terms.every(t => lastVisibilityByTerm[t] === false) || sample.final_grade === null;
                        if (allHidden) {
                            showState('grades-hidden');
                            return;
                        }
                    }

                    const passing = (sample.passing_grade !== undefined ? sample.passing_grade : null) || 75;

                    clearStates();
                    $('#grades-table').show();
                    const $thead = $('#grades-table thead').empty();
                    const $tbody = $('#grades-table tbody').empty();

                    $thead.append(buildHeader(terms, passing));

                    entries.sort(([a], [b]) => a.localeCompare(b));
                    entries.forEach(([studentName, sd]) => {
                        const termCells = terms.map(t => termCell(sd.term_grades && sd.term_grades[t], passing)).join('');
                        const final = sd.final_grade;
                        const finalCls = gradeClass(final, passing);
                        const finalHtml = final === null || final === undefined
                            ? `<span class="sg-final">--</span>`
                            : `<span class="sg-final ${finalCls}">${fmtGrade(final)}</span>`;
                        const transmuted = applyTransmutation(final);

                        $tbody.append(`
                            <tr>
                                <td class="sg-sticky text-start fw-semibold">${studentName}</td>
                                ${termCells}
                                <td>${finalHtml}</td>
                                <td class="fw-bold">${transmuted}</td>
                            </tr>
                        `);
                    });

                    applySearch();
                },
                error: (xhr) => {
                    showState('grades-no-data');
                    const msg = (xhr.responseJSON && xhr.responseJSON.error) || xhr.statusText || 'Unknown error';
                    Swal.fire({ icon: 'error', title: 'Failed to load grades', text: `${msg} (status ${xhr.status})` });
                }
            });
        }

        function applySearch() {
            const q = ($('#custom-search').val() || '').toLowerCase().trim();
            $('#grades-table tbody tr').each(function () {
                const name = $(this).find('td.sg-sticky').text().toLowerCase();
                $(this).toggle(!q || name.includes(q));
            });
        }

        $(document).on('click', '.sg-term-toggle', function () {
            if (!isTeacher) return;
            const termName = $(this).data('term');
            const termId = lastTermInfo[termName];
            const subjectId = $('#subject').val();
            if (!subjectId || !termId) return;

            const makeVisible = lastVisibilityByTerm[termName] === false;
            const $btn = $(this).prop('disabled', true);
            const originalHtml = $btn.html();
            $btn.html('<i class="fas fa-spinner fa-spin"></i>');

            $.ajax({
                url: '/toggle_grade_visibility/',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ subject_id: subjectId, term_id: termId, is_visible: makeVisible }),
                success: (resp) => {
                    toast('success', resp.message || 'Updated.');
                    fetchGrades();
                },
                error: (xhr) => {
                    $btn.prop('disabled', false).html(originalHtml);
                    const m = (xhr.responseJSON && xhr.responseJSON.message) || 'Failed to update visibility.';
                    toast('error', m);
                }
            });
        });

        $('#semester').on('change', function () {
            fetchSubjects($(this).val());
            $('#subject').val('').trigger('change');
            showState('grades-empty');
        });

        $('#subject').on('change', fetchGrades);
        $('#custom-search').on('input', applySearch);

        const defaultSem = $('#semester').val();
        if (defaultSem) fetchSubjects(defaultSem);
        showState('grades-empty');

        $('#download-excel').on('click', function () {
            if (!$('#grades-table').is(':visible')) {
                toast('warning', 'Please select a semester and subject first.');
                return;
            }
            try {
                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.table_to_sheet(document.getElementById('grades-table'));
                XLSX.utils.book_append_sheet(wb, ws, 'Student Grades');
                XLSX.writeFile(wb, `${selectedSubject}_${selectedSemester}_Grades.xlsx`);
                toast('success', 'Excel file downloaded.');
            } catch (e) {
                toast('error', 'Failed to generate Excel file.');
            }
        });
    });
    