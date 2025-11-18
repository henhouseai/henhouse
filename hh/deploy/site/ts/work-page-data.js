"use strict";
/**
 * WorkPageData - Base class for work pages (work docket, ask, task, step).
 * Provides shared functionality for status, meta, and sort_order fields.
 * This is an abstract base class - derived classes should extend this.
 */
var __extends = (this && this.__extends) || (function () {
    var extendStatics = function (d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };
    return function (d, b) {
        if (typeof b !== "function" && b !== null)
            throw new TypeError("Class extends value " + String(b) + " is not a constructor or null");
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.WorkPageData = void 0;
var page_data_js_1 = require("./page-data.js");
var page_manager_js_1 = require("./page-manager.js");
var overlay_manager_js_1 = require("./overlay-manager.js");
var WorkPageData = /** @class */ (function (_super) {
    __extends(WorkPageData, _super);
    function WorkPageData(data) {
        return _super.call(this, data) || this;
    }
    /**
     * Override to provide field mappings for work page fields.
     * Derived classes should call super.getFieldMappings() and add their own.
     */
    WorkPageData.prototype.getFieldMappings = function () {
        return __spreadArray(__spreadArray([], _super.prototype.getFieldMappings.call(this), true), [
            // Work page shared mappings
            {
                fields: ['status'],
                mcpTool: 'modify_work_status',
                priority: 0,
                buildParams: function (fields, values, pageId) { return ({
                    page_id: pageId,
                    status: values['status']
                }); }
            },
            {
                fields: ['sort_order'],
                mcpTool: 'modify_work_sort_order',
                priority: 0,
                buildParams: function (fields, values, pageId) { return ({
                    page_id: pageId,
                    sort_order: parseInt(values['sort_order']) || 0
                }); }
            }
        ], false);
    };
    /**
     * Handler for modify_work_status app action.
     * Shows a form with a dropdown to select the new status.
     */
    WorkPageData.prototype.modify_work_status = function (rpc) {
        return __awaiter(this, void 0, void 0, function () {
            var pageId, pageManager_1, currentStatus, formHtml;
            var _this = this;
            return __generator(this, function (_a) {
                pageId = this.id;
                if (!pageId) {
                    alert('No page ID found');
                    return [2 /*return*/];
                }
                try {
                    pageManager_1 = page_manager_js_1.PageManager.getInstance();
                    currentStatus = this.getField('status', 'form') || 'todo';
                    formHtml = "\n          <div class=\"overlay-form-group\">\n            <label>Status:</label>\n            <select id=\"page-field-status\" class=\"overlay-form-select\">\n              <option value=\"todo\" ".concat(currentStatus === 'todo' ? 'selected' : '', ">Todo</option>\n              <option value=\"doing\" ").concat(currentStatus === 'doing' ? 'selected' : '', ">Doing</option>\n              <option value=\"review\" ").concat(currentStatus === 'review' ? 'selected' : '', ">Review</option>\n              <option value=\"done\" ").concat(currentStatus === 'done' ? 'selected' : '', ">Done</option>\n            </select>\n          </div>\n      ");
                    overlay_manager_js_1.OverlayManager.getInstance().show({
                        header: 'Modify Work Status',
                        content: [formHtml],
                        contentHeaders: [''],
                        closable: true,
                        submitLabel: 'Submit',
                        cancelLabel: 'Cancel',
                        onCancel: function () {
                            pageManager_1.clearFieldRegistry();
                        },
                        onUnmount: function () {
                            pageManager_1.clearFieldRegistry();
                        },
                        onSubmit: function () { return __awaiter(_this, void 0, void 0, function () {
                            var changedFields, editableFields, optimalMappings, currentValues, result, allSucceeded;
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0:
                                        changedFields = pageManager_1['detectChangedFields']();
                                        editableFields = changedFields.filter(function (field) { return field !== 'class'; });
                                        if (editableFields.length === 0) {
                                            return [2 /*return*/, { success: true, noChanges: true, _showMessage: 'No changes made', _autoFade: true }];
                                        }
                                        optimalMappings = pageManager_1['selectOptimalMappings'](editableFields);
                                        currentValues = pageManager_1['extractFormValues']();
                                        if (!pageId) {
                                            throw new Error('No page ID available');
                                        }
                                        return [4 /*yield*/, this.processOperationsIncrementally(rpc, optimalMappings, currentValues, pageId)];
                                    case 1:
                                        result = _a.sent();
                                        allSucceeded = result.success && result.errors.length === 0;
                                        if (allSucceeded) {
                                            // Update internal data
                                            if ('status' in currentValues) {
                                                this.updateFieldValue('status', currentValues['status']);
                                            }
                                            return [2 /*return*/, {
                                                    success: true,
                                                    _showMessage: 'Status updated successfully',
                                                    _autoFade: true,
                                                    debug: result.debug
                                                }];
                                        }
                                        else {
                                            // Errors already shown in overlay
                                            return [2 /*return*/, {
                                                    success: false,
                                                    debug: result.debug
                                                }];
                                        }
                                        return [2 /*return*/];
                                }
                            });
                        }); }
                    });
                }
                catch (error) {
                    rpc.showError('modify_work_status', error);
                }
                return [2 /*return*/];
            });
        });
    };
    /**
     * Handler for modify_work_meta_set_all app action.
     * Shows a table form with key-value pairs that can be added, removed, and reordered.
     */
    WorkPageData.prototype.modify_work_meta_set_all = function (rpc) {
        return __awaiter(this, void 0, void 0, function () {
            var pageId, currentMeta, metaObj_1, pairs, tableId_1, tableHtml_1;
            var _this = this;
            return __generator(this, function (_a) {
                pageId = this.id;
                if (!pageId) {
                    alert('No page ID found');
                    return [2 /*return*/];
                }
                try {
                    currentMeta = this.getField('meta', 'form') || '{}';
                    metaObj_1 = {};
                    try {
                        if (currentMeta && currentMeta.trim()) {
                            metaObj_1 = JSON.parse(currentMeta);
                        }
                    }
                    catch (e) {
                        // Invalid JSON, start with empty object
                        metaObj_1 = {};
                    }
                    pairs = Object.keys(metaObj_1).map(function (key) { return ({
                        key: key,
                        value: typeof metaObj_1[key] === 'string' ? metaObj_1[key] : JSON.stringify(metaObj_1[key])
                    }); });
                    // If empty, start with one empty row
                    if (pairs.length === 0) {
                        pairs.push({ key: '', value: '' });
                    }
                    tableId_1 = 'meta-table-' + Date.now();
                    tableHtml_1 = "\n        <div class=\"overlay-form-group\">\n          <label>Meta Key-Value Pairs:</label>\n          <table id=\"".concat(tableId_1, "\" class=\"meta-key-value-table\" style=\"width: 100%; border-collapse: collapse; margin-top: 10px;\">\n            <thead>\n              <tr>\n                <th style=\"width: 40%; padding: 8px; border: 1px solid #ddd; background: #f5f5f5;\">Key</th>\n                <th style=\"width: 55%; padding: 8px; border: 1px solid #ddd; background: #f5f5f5;\">Value</th>\n                <th style=\"width: 5%; padding: 8px; border: 1px solid #ddd; background: #f5f5f5;\"></th>\n              </tr>\n            </thead>\n            <tbody id=\"").concat(tableId_1, "-tbody\">\n      ");
                    // Add rows for existing pairs
                    pairs.forEach(function (pair, index) {
                        var rowId = "".concat(tableId_1, "-row-").concat(index);
                        tableHtml_1 += "\n          <tr id=\"".concat(rowId, "\" draggable=\"true\" style=\"cursor: move;\">\n            <td style=\"padding: 4px; border: 1px solid #ddd;\">\n              <input type=\"text\" class=\"meta-key-input\" value=\"").concat(_this.escapeHtml(pair.key), "\" \n                     style=\"width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;\" \n                     placeholder=\"Key (no spaces, JSON valid)\">\n            </td>\n            <td style=\"padding: 4px; border: 1px solid #ddd;\">\n              <input type=\"text\" class=\"meta-value-input\" value=\"").concat(_this.escapeHtml(pair.value), "\" \n                     style=\"width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;\" \n                     placeholder=\"Value (can be JSON string)\">\n            </td>\n            <td style=\"padding: 4px; border: 1px solid #ddd; text-align: center;\">\n              <button type=\"button\" class=\"meta-remove-btn\" style=\"background: #dc3545; color: white; border: none; padding: 4px 8px; cursor: pointer; border-radius: 3px;\">\u00D7</button>\n            </td>\n          </tr>\n        ");
                    });
                    tableHtml_1 += "\n            </tbody>\n          </table>\n          <button type=\"button\" id=\"".concat(tableId_1, "-add-btn\" style=\"margin-top: 10px; padding: 6px 12px; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 3px;\">Add Row</button>\n          <div class=\"overlay-form-help\" style=\"margin-top: 10px;\">Keys must be JSON valid (no spaces). Values can be strings or JSON. Drag rows to reorder.</div>\n        </div>\n      ");
                    overlay_manager_js_1.OverlayManager.getInstance().show({
                        header: 'Modify Meta',
                        content: [tableHtml_1],
                        contentHeaders: [''],
                        closable: true,
                        submitLabel: 'Submit',
                        cancelLabel: 'Cancel',
                        onCancel: function () {
                            // Cleanup
                        },
                        onUnmount: function () {
                            // Cleanup
                        },
                        onSubmit: function () { return __awaiter(_this, void 0, void 0, function () {
                            var tbody, rows, pairs, _i, rows_1, row, keyInput, valueInput, key, value, parsedValue, metaObj, _a, pairs_1, _b, key, value, metaJson, params, result, hasDebugData, handleRPCResponseWithDebug, error_1, hasDebugData, handleRPCResponseWithDebug;
                            return __generator(this, function (_c) {
                                switch (_c.label) {
                                    case 0:
                                        tbody = document.querySelector("#".concat(tableId_1, "-tbody"));
                                        if (!tbody) {
                                            throw new Error('Table not found');
                                        }
                                        rows = Array.from(tbody.querySelectorAll('tr'));
                                        pairs = [];
                                        for (_i = 0, rows_1 = rows; _i < rows_1.length; _i++) {
                                            row = rows_1[_i];
                                            keyInput = row.querySelector('.meta-key-input');
                                            valueInput = row.querySelector('.meta-value-input');
                                            if (keyInput && valueInput) {
                                                key = keyInput.value.trim();
                                                value = valueInput.value.trim();
                                                // Skip empty keys
                                                if (!key)
                                                    continue;
                                                // Validate key (no spaces, JSON valid)
                                                if (key.includes(' ')) {
                                                    throw new Error("Key \"".concat(key, "\" contains spaces. Keys must be JSON valid (no spaces)."));
                                                }
                                                parsedValue = void 0;
                                                try {
                                                    parsedValue = JSON.parse(value);
                                                }
                                                catch (e) {
                                                    parsedValue = value;
                                                }
                                                pairs.push([key, parsedValue]);
                                            }
                                        }
                                        metaObj = {};
                                        for (_a = 0, pairs_1 = pairs; _a < pairs_1.length; _a++) {
                                            _b = pairs_1[_a], key = _b[0], value = _b[1];
                                            metaObj[key] = value;
                                        }
                                        metaJson = JSON.stringify(metaObj);
                                        _c.label = 1;
                                    case 1:
                                        _c.trys.push([1, 5, , 8]);
                                        params = {
                                            page_id: pageId,
                                            meta: metaJson
                                        };
                                        return [4 /*yield*/, rpc.call('modify_work_meta_set_all', params)];
                                    case 2:
                                        result = _c.sent();
                                        hasDebugData = (result === null || result === void 0 ? void 0 : result.debug) && Array.isArray(result.debug.entries) && result.debug.entries.length > 0;
                                        if (!hasDebugData) return [3 /*break*/, 4];
                                        return [4 /*yield*/, Promise.resolve().then(function () { return require('./debug-helper.js'); })];
                                    case 3:
                                        handleRPCResponseWithDebug = (_c.sent()).handleRPCResponseWithDebug;
                                        handleRPCResponseWithDebug(result, 'modify_work_meta_set_all', params);
                                        _c.label = 4;
                                    case 4:
                                        if (result && result.success !== false) {
                                            // Update internal data
                                            this.updateFieldValue('meta', metaJson);
                                            return [2 /*return*/, {
                                                    success: true,
                                                    _showMessage: 'Meta updated successfully',
                                                    _autoFade: !hasDebugData, // Disable auto-fade if debug data is present
                                                    debug: result.debug
                                                }];
                                        }
                                        else {
                                            // Server returned error - include debug data if present
                                            throw new Error((result === null || result === void 0 ? void 0 : result.error) || 'Failed to update meta');
                                        }
                                        return [3 /*break*/, 8];
                                    case 5:
                                        error_1 = _c.sent();
                                        hasDebugData = (error_1 === null || error_1 === void 0 ? void 0 : error_1.debug) && Array.isArray(error_1.debug.entries) && error_1.debug.entries.length > 0;
                                        if (!hasDebugData) return [3 /*break*/, 7];
                                        return [4 /*yield*/, Promise.resolve().then(function () { return require('./debug-helper.js'); })];
                                    case 6:
                                        handleRPCResponseWithDebug = (_c.sent()).handleRPCResponseWithDebug;
                                        handleRPCResponseWithDebug(error_1, 'modify_work_meta_set_all', {
                                            page_id: pageId,
                                            meta: metaJson
                                        });
                                        _c.label = 7;
                                    case 7: throw error_1;
                                    case 8: return [2 /*return*/];
                                }
                            });
                        }); }
                    });
                    // Set up event handlers after overlay is shown
                    setTimeout(function () {
                        var tbody = document.querySelector("#".concat(tableId_1, "-tbody"));
                        var addBtn = document.querySelector("#".concat(tableId_1, "-add-btn"));
                        if (!tbody || !addBtn)
                            return;
                        // Add row button handler
                        addBtn.addEventListener('click', function () {
                            var newRow = document.createElement('tr');
                            newRow.setAttribute('draggable', 'true');
                            newRow.style.cursor = 'move';
                            newRow.innerHTML = "\n            <td style=\"padding: 4px; border: 1px solid #ddd;\">\n              <input type=\"text\" class=\"meta-key-input\" value=\"\" \n                     style=\"width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;\" \n                     placeholder=\"Key (no spaces, JSON valid)\">\n            </td>\n            <td style=\"padding: 4px; border: 1px solid #ddd;\">\n              <input type=\"text\" class=\"meta-value-input\" value=\"\" \n                     style=\"width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;\" \n                     placeholder=\"Value (can be JSON string)\">\n            </td>\n            <td style=\"padding: 4px; border: 1px solid #ddd; text-align: center;\">\n              <button type=\"button\" class=\"meta-remove-btn\" style=\"background: #dc3545; color: white; border: none; padding: 4px 8px; cursor: pointer; border-radius: 3px;\">\u00D7</button>\n            </td>\n          ";
                            tbody.appendChild(newRow);
                            // Add another empty row below (auto-add feature)
                            var autoRow = document.createElement('tr');
                            autoRow.setAttribute('draggable', 'true');
                            autoRow.style.cursor = 'move';
                            autoRow.innerHTML = "\n            <td style=\"padding: 4px; border: 1px solid #ddd;\">\n              <input type=\"text\" class=\"meta-key-input\" value=\"\" \n                     style=\"width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;\" \n                     placeholder=\"Key (no spaces, JSON valid)\">\n            </td>\n            <td style=\"padding: 4px; border: 1px solid #ddd;\">\n              <input type=\"text\" class=\"meta-value-input\" value=\"\" \n                     style=\"width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;\" \n                     placeholder=\"Value (can be JSON string)\">\n            </td>\n            <td style=\"padding: 4px; border: 1px solid #ddd; text-align: center;\">\n              <button type=\"button\" class=\"meta-remove-btn\" style=\"background: #dc3545; color: white; border: none; padding: 4px 8px; cursor: pointer; border-radius: 3px;\">\u00D7</button>\n            </td>\n          ";
                            tbody.appendChild(autoRow);
                            // Attach remove handler to new buttons
                            attachRemoveHandlers();
                        });
                        // Remove button handlers
                        var attachRemoveHandlers = function () {
                            var removeBtns = tbody.querySelectorAll('.meta-remove-btn');
                            removeBtns.forEach(function (btn) {
                                btn.addEventListener('click', function (e) {
                                    var row = e.target.closest('tr');
                                    if (row && tbody.children.length > 1) {
                                        row.remove();
                                    }
                                    else if (row) {
                                        // If last row, just clear it
                                        var keyInput = row.querySelector('.meta-key-input');
                                        var valueInput = row.querySelector('.meta-value-input');
                                        if (keyInput)
                                            keyInput.value = '';
                                        if (valueInput)
                                            valueInput.value = '';
                                    }
                                });
                            });
                        };
                        attachRemoveHandlers();
                        // Drag and drop handlers
                        var draggedRow = null;
                        tbody.querySelectorAll('tr').forEach(function (row) {
                            row.addEventListener('dragstart', function (e) {
                                draggedRow = row;
                                row.style.opacity = '0.5';
                            });
                            row.addEventListener('dragend', function () {
                                if (draggedRow) {
                                    draggedRow.style.opacity = '1';
                                    draggedRow = null;
                                }
                            });
                            row.addEventListener('dragover', function (e) {
                                e.preventDefault();
                                var target = e.target;
                                var targetRow = target.closest('tr');
                                if (targetRow && targetRow !== draggedRow && draggedRow) {
                                    var rect = targetRow.getBoundingClientRect();
                                    var next = (e.clientY - rect.top) / (rect.bottom - rect.top) > 0.5;
                                    if (next) {
                                        tbody.insertBefore(draggedRow, targetRow.nextSibling);
                                    }
                                    else {
                                        tbody.insertBefore(draggedRow, targetRow);
                                    }
                                }
                            });
                            row.addEventListener('drop', function (e) {
                                e.preventDefault();
                            });
                        });
                    }, 100);
                }
                catch (error) {
                    rpc.showError('modify_work_meta_set_all', error);
                }
                return [2 /*return*/];
            });
        });
    };
    /**
     * Escape HTML to prevent XSS
     */
    WorkPageData.prototype.escapeHtml = function (text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };
    /**
     * Handler for modify_work_sort_order app action.
     * Shows a form with a text input to set the new sort_order position.
     */
    WorkPageData.prototype.modify_work_sort_order = function (rpc) {
        return __awaiter(this, void 0, void 0, function () {
            var pageId, pageManager_2, currentSortOrder, formHtml;
            var _this = this;
            return __generator(this, function (_a) {
                pageId = this.id;
                if (!pageId) {
                    alert('No page ID found');
                    return [2 /*return*/];
                }
                try {
                    pageManager_2 = page_manager_js_1.PageManager.getInstance();
                    currentSortOrder = this.getField('sort_order', 'form') || 0;
                    formHtml = "\n          <div class=\"overlay-form-group\">\n            <label>Sort Order:</label>\n            <input type=\"number\" id=\"page-field-sort_order\" value=\"".concat(currentSortOrder, "\" class=\"overlay-form-input\" min=\"1\">\n            <div class=\"overlay-form-help\">Enter the position (1-based). Values \u2264 0 go to beginning, values too high go to end.</div>\n          </div>\n      ");
                    overlay_manager_js_1.OverlayManager.getInstance().show({
                        header: 'Modify Work Sort Order',
                        content: [formHtml],
                        contentHeaders: [''],
                        closable: true,
                        submitLabel: 'Submit',
                        cancelLabel: 'Cancel',
                        onCancel: function () {
                            pageManager_2.clearFieldRegistry();
                        },
                        onUnmount: function () {
                            pageManager_2.clearFieldRegistry();
                        },
                        onSubmit: function () { return __awaiter(_this, void 0, void 0, function () {
                            var changedFields, editableFields, optimalMappings, currentValues, result, allSucceeded;
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0:
                                        changedFields = pageManager_2['detectChangedFields']();
                                        editableFields = changedFields.filter(function (field) { return field !== 'class'; });
                                        if (editableFields.length === 0) {
                                            return [2 /*return*/, { success: true, noChanges: true, _showMessage: 'No changes made', _autoFade: true }];
                                        }
                                        optimalMappings = pageManager_2['selectOptimalMappings'](editableFields);
                                        currentValues = pageManager_2['extractFormValues']();
                                        if (!pageId) {
                                            throw new Error('No page ID available');
                                        }
                                        return [4 /*yield*/, this.processOperationsIncrementally(rpc, optimalMappings, currentValues, pageId)];
                                    case 1:
                                        result = _a.sent();
                                        allSucceeded = result.success && result.errors.length === 0;
                                        if (allSucceeded) {
                                            // Update internal data
                                            if ('sort_order' in currentValues) {
                                                this.updateFieldValue('sort_order', currentValues['sort_order']);
                                            }
                                            return [2 /*return*/, {
                                                    success: true,
                                                    _showMessage: 'Sort order updated successfully',
                                                    _autoFade: true,
                                                    debug: result.debug
                                                }];
                                        }
                                        else {
                                            // Errors already shown in overlay
                                            return [2 /*return*/, {
                                                    success: false,
                                                    debug: result.debug
                                                }];
                                        }
                                        return [2 /*return*/];
                                }
                            });
                        }); }
                    });
                }
                catch (error) {
                    rpc.showError('modify_work_sort_order', error);
                }
                return [2 /*return*/];
            });
        });
    };
    return WorkPageData;
}(page_data_js_1.PageData));
exports.WorkPageData = WorkPageData;
