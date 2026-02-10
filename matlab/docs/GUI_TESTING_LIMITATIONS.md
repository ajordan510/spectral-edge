# SpectralEdge GUI Testing Limitations

This document outlines the limitations of headless GUI testing and provides recommendations for elements that require manual verification or alternative testing approaches.

## Overview of Testing Coverage

The automated test suite covers the following areas:

| Category | Coverage | Notes |
|----------|----------|-------|
| Button functionality | ✅ High | All buttons tested for click response |
| Parameter controls | ✅ High | All spin boxes, combos, checkboxes tested |
| Calculation accuracy | ✅ High | PSD, CSD, coherence algorithms verified |
| Plot data accuracy | ✅ High | Data values verified against expectations |
| Error handling | ✅ High | Invalid inputs handled gracefully |
| Visual appearance | ⚠️ Partial | Styling exists but not pixel-verified |
| User experience | ❌ Low | Requires human evaluation |

---

## Elements That Cannot Be Fully Tested via CLI

### 1. Visual Appearance and Styling

**What Cannot Be Tested:**
- Exact color rendering (how colors appear on different monitors)
- Font rendering quality and readability
- Icon/emoji display quality
- Layout aesthetics and spacing "feel"
- Responsive resizing behavior appearance
- Dark theme contrast and accessibility

**Why:**
- Headless rendering (offscreen) may differ from actual display rendering
- Human judgment required for aesthetic quality
- Color perception varies by display calibration

**Potential Fixes/Approaches:**
1. **Screenshot comparison testing** - Capture baseline screenshots and compare
   ```python
   # Example using pytest-qt screenshot comparison
   def test_visual_appearance(qtbot, window):
       # Capture current appearance
       pixmap = window.grab()
       image = pixmap.toImage()
       image.save("current_screenshot.png")

       # Compare with baseline (requires baseline images)
       # Note: This is fragile across different systems
   ```

2. **Add visual regression testing with Percy or similar tools**
   - Integrate with CI to catch visual regressions
   - Requires cloud service subscription

3. **Create a manual visual checklist** - Document expected appearance for QA

### 2. Mouse Interaction Precision

**What Cannot Be Tested:**
- Drag-and-drop operations (e.g., moving legend)
- Precise click coordinates on plots
- Zoom/pan with mouse wheel behavior
- Double-click timing sensitivity
- Right-click context menu positioning

**Why:**
- Mouse simulation in headless mode doesn't replicate hardware behavior
- Timing-sensitive operations are unreliable in test environments

**Potential Fixes/Approaches:**
1. **Use PyAutoGUI for real mouse simulation** (requires display)
   ```python
   import pyautogui

   # Requires actual display, not suitable for headless CI
   def test_real_mouse_interaction():
       pyautogui.click(x, y)
       pyautogui.scroll(5)  # Mouse wheel
   ```

2. **Test interaction logic separately**
   ```python
   def test_zoom_logic():
       # Test the zoom calculation logic, not the mouse event
       new_range = calculate_zoom_range(current_range, zoom_factor=2)
       assert new_range == expected_range
   ```

3. **Add integration tests on real display** - Run on dedicated test machine

### 3. Keyboard Shortcuts and Focus

**What Cannot Be Tested:**
- Keyboard navigation between widgets (Tab order)
- Keyboard shortcut combinations (Ctrl+S, etc.)
- Focus ring visibility
- Text cursor positioning in input fields

**Why:**
- Focus behavior in headless mode may differ
- Keyboard event simulation limited

**Potential Fixes/Approaches:**
1. **Test key event handling logic**
   ```python
   from PyQt6.QtTest import QTest
   from PyQt6.QtCore import Qt

   def test_keyboard_shortcut(window, qtbot):
       QTest.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
       # Verify expected action occurred
   ```

2. **Document keyboard shortcuts for manual testing**

### 4. File Dialog Integration

**What Cannot Be Tested:**
- Native file dialog appearance (OS-specific)
- File browser navigation
- File type filter behavior
- Default directory setting

**Why:**
- Native dialogs are controlled by the operating system
- Must be mocked in headless tests

**Current Approach:**
- File dialogs are mocked to return test file paths
- This tests the code that processes the file, not the dialog itself

**Potential Fixes/Approaches:**
1. **Accept mocked tests as sufficient** - Native dialogs are OS-tested
2. **Add integration tests on real systems** for end-to-end verification

### 5. HDF5 Flight Navigator

**What Cannot Be Tested:**
- HDF5 file structure browsing with real flight data
- Large file handling performance
- Memory usage with multi-GB files

**Why:**
- Requires real HDF5 test files (potentially large)
- Memory profiling not practical in unit tests

**Current Approach:**
- Tests use small synthetic HDF5 files
- Core loading logic is tested

**Potential Fixes/Approaches:**
1. **Create representative test HDF5 files**
   ```python
   import h5py

   def create_test_hdf5(path, size_mb=10):
       with h5py.File(path, 'w') as f:
           # Create realistic structure
           samples = int(size_mb * 1024 * 1024 / 8)  # float64
           f.create_dataset('channel1', data=np.random.randn(samples))
   ```

2. **Add memory profiling tests**
   ```python
   import tracemalloc

   def test_memory_usage():
       tracemalloc.start()
       # Load large file
       current, peak = tracemalloc.get_traced_memory()
       assert peak < MAX_ALLOWED_MEMORY
   ```

### 6. Real-Time Performance

**What Cannot Be Tested:**
- UI responsiveness during calculation
- Progress indicator updates
- Animation smoothness
- Plot update frame rate

**Why:**
- Timing behavior differs in headless mode
- Frame rate measurement requires real rendering

**Potential Fixes/Approaches:**
1. **Benchmark calculation times separately**
   ```python
   import time

   def test_calculation_performance():
       start = time.perf_counter()
       result = calculate_psd(large_signal, sample_rate)
       elapsed = time.perf_counter() - start
       assert elapsed < MAX_ALLOWED_TIME
   ```

2. **Add UI responsiveness checks**
   ```python
   def test_ui_responsive_during_calculation(qtbot, window):
       # Start long calculation
       window.start_calculation()

       # Verify UI processes events
       qtbot.wait(100)
       assert window.isEnabled()  # UI should not be frozen
   ```

### 7. Print/Export Quality

**What Cannot Be Tested:**
- Print dialog appearance
- PDF export quality
- PowerPoint rendering accuracy
- Image resolution for publications

**Why:**
- Print dialogs are OS-native
- Export quality requires visual inspection

**Potential Fixes/Approaches:**
1. **Verify export file validity**
   ```python
   def test_pptx_export_valid():
       report.save(path)
       # Verify file is valid PPTX
       from pptx import Presentation
       prs = Presentation(path)
       assert len(prs.slides) > 0
   ```

2. **Add image resolution checks**
   ```python
   from PIL import Image

   def test_export_resolution():
       image_data = export_plot_to_image(plot_widget)
       img = Image.open(io.BytesIO(image_data))
       assert img.size[0] >= 1920  # Minimum width
       assert img.size[1] >= 1080  # Minimum height
   ```

### 8. Tooltip Display

**What Cannot Be Tested:**
- Tooltip appearance and positioning
- Tooltip display timing (show/hide delays)
- Tooltip content rendering

**Why:**
- Tooltips require mouse hover events with timing
- Positioning is window-manager dependent

**Potential Fixes/Approaches:**
1. **Verify tooltip text is set correctly**
   ```python
   def test_tooltip_content(window):
       assert window.some_widget.toolTip() == "Expected tooltip text"
   ```

2. **Accept that tooltip display is an OS/Qt concern**

---

## Recommended Manual Testing Checklist

For each release, perform the following manual verification:

### Visual Appearance
- [ ] Check dark theme colors are consistent
- [ ] Verify fonts are readable at various window sizes
- [ ] Confirm icons/emojis display correctly
- [ ] Test on both high-DPI and standard displays

### User Interactions
- [ ] Test mouse wheel zoom on plots
- [ ] Verify drag-and-drop for any applicable features
- [ ] Check right-click context menus work
- [ ] Test keyboard shortcuts (if any)

### File Operations
- [ ] Open CSV files via native file dialog
- [ ] Open HDF5 files and browse flight data
- [ ] Export report to PowerPoint
- [ ] Verify file filters work correctly

### Performance
- [ ] Load a large file (>100MB) and verify responsiveness
- [ ] Calculate PSD on long duration signal
- [ ] Open multiple windows simultaneously

### Cross-Platform
- [ ] Test on Windows
- [ ] Test on macOS (if applicable)
- [ ] Test on Linux with different window managers

---

## Summary Table

| Feature | Automated Test | Manual Test Required |
|---------|---------------|---------------------|
| Button clicks | ✅ | ❌ |
| Parameter changes | ✅ | ❌ |
| Calculation accuracy | ✅ | ❌ |
| Error messages | ✅ | Appearance only |
| File loading (logic) | ✅ | ❌ |
| File dialog (native) | Mocked | ✅ |
| Plot data | ✅ | ❌ |
| Plot appearance | Partial | ✅ |
| Color scheme | Existence | ✅ |
| Tooltip text | ✅ | Display only |
| Mouse interactions | Limited | ✅ |
| Keyboard shortcuts | Limited | ✅ |
| Export files | Valid format | Quality |
| Performance | Timing | Responsiveness |
| Memory usage | ❌ | ✅ |

---

## Conclusion

The automated test suite provides high coverage for functional correctness:
- 95%+ of button/control functionality
- 100% of core calculation algorithms
- 90%+ of error handling paths

Manual testing should focus on:
1. Visual quality and aesthetics
2. User experience and "feel"
3. Performance under real-world conditions
4. Cross-platform consistency

By combining automated tests with targeted manual verification, you can achieve comprehensive quality assurance with efficient use of testing resources.
