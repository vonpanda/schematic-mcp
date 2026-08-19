/*
 * Synthetic firmware fixture for schematic-mcp.
 *
 * This file intentionally swaps SENSOR_INT and LED_STATUS GPIO assignments so
 * the firmware-vs-schematic demo has a deterministic mismatch to detect.
 */

#define I2C_SDA_GPIO 8
#define I2C_SCL_GPIO 9
#define SENSOR_INT_GPIO 13
#define LED_STATUS_GPIO 12

void app_init(void) {
    /* Peripheral initialization is omitted; only the pin contract matters here. */
}
